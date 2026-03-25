#!/usr/bin/env python3
"""
Persistent code-change monitoring agents.

Watches git for new commits and runs 5 specialized agents via the Claude CLI in parallel:
  1. Regression   — broken interfaces, removed functionality, schema drift
  2. Deletions    — large or suspicious deletions
  3. Security     — unsafe practices, secrets, injection risks
  4. Rules        — CLAUDE.md violations, unjustified config/infra changes
  5. Bugs         — logic errors, uncaught exceptions, type mismatches

Requires: 'claude' CLI on PATH (uses existing Claude Code auth).

Run continuously:
  python3 .claude/monitors/monitor_agents.py

Run once (CI / one-shot check):
  python3 .claude/monitors/monitor_agents.py --once

Alerts are written to .claude/monitors/alerts.log
"""

import os
import shutil
import sys
import time
import json
import argparse
import threading
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────

REPO_ROOT      = Path(__file__).resolve().parents[2]
STATE_FILE     = Path(__file__).parent / "last_checked.sha"
ALERTS_LOG     = Path(__file__).parent / "alerts.log"
POLL_INTERVAL  = 120          # seconds between git polls
MODEL          = "claude-sonnet-4-6"
MAX_DIFF_CHARS = 24_000       # truncate huge diffs to stay within token budget

# ── Agent definitions ────────────────────────────────────────────────────────

AGENTS = {
    "regression": {
        "system": textwrap.dedent("""\
            You are a regression-detection agent. Analyse the git diff below.
            Flag ONLY issues with HIGH confidence. Focus on:
            - Removed or renamed public functions/classes/endpoints that callers depend on
            - Changed function signatures (arguments added/removed, types changed)
            - Deleted test files or test cases that covered existing behaviour
            - Database schema changes (columns dropped, types altered, constraints removed)
            - Config keys removed that other modules reference
            - Import paths changed without updating all consumers

            Respond with a JSON object:
            {"severity": "ok"|"warning"|"critical", "issues": [{"type": "...", "location": "file:line", "detail": "..."}]}
            If nothing is wrong, return {"severity": "ok", "issues": []}.
        """),
    },
    "deletions": {
        "system": textwrap.dedent("""\
            You are a deletion-analysis agent. Analyse the git diff below.
            Flag ONLY issues with HIGH confidence. Focus on:
            - Single files losing more than 40 lines of substantive code
            - Entire files deleted — especially tests, migrations, config files
            - Blocks of error-handling, validation, or guard logic removed
            - Safety checks or authentication logic removed
            - Commented-out code that silently disables existing behaviour

            Respond with a JSON object:
            {"severity": "ok"|"warning"|"critical", "issues": [{"type": "...", "location": "file:line", "detail": "..."}]}
            If nothing is suspicious, return {"severity": "ok", "issues": []}.
        """),
    },
    "security": {
        "system": textwrap.dedent("""\
            You are a security code-review agent. Analyse the git diff below.
            Flag ONLY issues with HIGH confidence. Focus on:
            - Hardcoded secrets, API keys, passwords, tokens (even partial/test values)
            - SQL injection via string formatting into queries
            - OS command injection (shell=True with untrusted input, os.system with f-strings)
            - Unsafe deserialization of untrusted data
            - Path traversal (user input in file paths without sanitisation)
            - Disabled TLS verification (verify=False, CERT_NONE)
            - Sensitive values echoed to logs
            - Missing authentication on new API endpoints

            Respond with a JSON object:
            {"severity": "ok"|"warning"|"critical", "issues": [{"type": "...", "location": "file:line", "detail": "..."}]}
            If nothing is unsafe, return {"severity": "ok", "issues": []}.
        """),
    },
    "rules": {
        "system": textwrap.dedent("""\
            You are a rule-compliance agent for a Python/FastAPI financial-data project.
            The project's CLAUDE.md mandates:
            - Milestone commits at every confirmed-working state (format: milestone(<subsystem>): ...)
            - No Ollama references in coding/cockpit paths (llama.cpp via OpenClaw is preferred)
            - No credentials, API keys, or secrets committed
            - Infrastructure changes (.mcp.json, settings.json, hooks, .env.example) must be
              accompanied by doc updates in docs/claude/
            - No placeholder code in production paths
            - No unrelated refactors bundled with feature changes
            - CLAUDE.md itself must not be silently weakened (rules removed or loosened)
              without explicit justification in the commit message

            Analyse the git diff below and flag violations.

            Respond with a JSON object:
            {"severity": "ok"|"warning"|"critical", "issues": [{"type": "...", "location": "file:line", "detail": "..."}]}
            If compliant, return {"severity": "ok", "issues": []}.
        """),
    },
    "bugs": {
        "system": textwrap.dedent("""\
            You are a bug-detection agent. Analyse the git diff below.
            Flag ONLY issues with HIGH confidence. Focus on:
            - Off-by-one errors and fence-post mistakes
            - None/null dereference without guards
            - Wrong variable used (copy-paste errors, shadowed names)
            - Incorrect boolean logic (inverted conditions, and/or confusion)
            - Missing await on async calls, or await on non-async functions
            - Uncaught exceptions from I/O, network, or DB operations in critical paths
            - Mutation of shared state without locks in threaded code
            - Incorrect use of mutable defaults in function signatures
            - Return values ignored when they carry error signals
            - Type mismatches (string vs int in arithmetic, bytes vs str)

            Respond with a JSON object:
            {"severity": "ok"|"warning"|"critical", "issues": [{"type": "...", "location": "file:line", "detail": "..."}]}
            If nothing is suspicious, return {"severity": "ok", "issues": []}.
        """),
    },
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def git(*args) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def get_current_sha() -> str:
    return git("rev-parse", "HEAD")


def get_last_checked_sha() -> str | None:
    if STATE_FILE.exists():
        sha = STATE_FILE.read_text().strip()
        return sha if sha else None
    return None


def save_last_checked_sha(sha: str) -> None:
    STATE_FILE.write_text(sha + "\n")


def get_diff_since(base_sha: str) -> str:
    diff = git("diff", base_sha, "HEAD", "--unified=3")
    if not diff:
        diff = git("diff", base_sha)
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n\n[... diff truncated for token budget ...]"
    return diff


def _write_alert(line: str) -> None:
    with open(ALERTS_LOG, "a") as f:
        f.write(line + "\n")
    print(line, flush=True)


def log_alert(agent_name: str, severity: str, issues: list, base_sha: str, head_sha: str) -> None:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_alert(f"[{ts}] [{agent_name.upper()}] severity={severity}  ({base_sha[:8]}..{head_sha[:8]})")
    for issue in issues:
        loc = issue.get("location", "?")
        typ = issue.get("type", "?")
        det = issue.get("detail", "")
        _write_alert(f"  ⚠  {typ} @ {loc}: {det}")
    _write_alert("")


def log_ok(agent_name: str, base_sha: str, head_sha: str) -> None:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{ts}] [{agent_name.upper()}] ok  ({base_sha[:8]}..{head_sha[:8]})", flush=True)

# ── Per-agent runner ─────────────────────────────────────────────────────────

def run_agent(name: str, spec: dict, diff: str, base_sha: str, head_sha: str) -> None:
    tag = name.upper()
    raw_lines: list[str] = []
    try:
        prompt = f"{spec['system']}\n\nAnalyse this git diff:\n\n```diff\n{diff}\n```"
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"[{ts}] [{tag}] ▶ started", flush=True)

        proc = subprocess.Popen(
            ["claude", "-p", "--model", MODEL, "--output-format", "text"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=REPO_ROOT,
        )
        # Send prompt and close stdin so the CLI starts processing
        proc.stdin.write(prompt)
        proc.stdin.close()

        # Stream stdout line-by-line with agent prefix
        for line in proc.stdout:
            line = line.rstrip("\n")
            raw_lines.append(line)
            print(f"  [{tag}] {line}", flush=True)

        proc.wait(timeout=90)
        stderr_out = proc.stderr.read()

        if proc.returncode != 0:
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
            _write_alert(f"[{ts}] [{tag}] CLI error (rc={proc.returncode}): {stderr_out[:300]}")
            return

        raw = "\n".join(raw_lines).strip()

        # Claude sometimes wraps JSON in markdown fences — strip them
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data     = json.loads(raw)
        severity = data.get("severity", "ok")
        issues   = data.get("issues", [])

        if severity == "ok" or not issues:
            log_ok(name, base_sha, head_sha)
        else:
            log_alert(name, severity, issues, base_sha, head_sha)

        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"[{ts}] [{tag}] ■ done — {severity}, {len(issues)} issue(s)", flush=True)

    except json.JSONDecodeError as e:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        raw = "\n".join(raw_lines).strip()
        _write_alert(f"[{ts}] [{tag}] JSON parse error: {e} — raw: {raw[:300]}")
    except subprocess.TimeoutExpired:
        proc.kill()
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _write_alert(f"[{ts}] [{tag}] CLI timeout (90s)")
    except Exception as e:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _write_alert(f"[{ts}] [{tag}] ERROR: {e}")

# ── Main loop ────────────────────────────────────────────────────────────────

def check_once() -> None:
    head_sha = get_current_sha()
    base_sha = get_last_checked_sha()

    if base_sha is None:
        base_sha = git("rev-parse", "HEAD~1") or head_sha
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"[{ts}] First run — baseline set to {base_sha[:8]}", flush=True)

    if base_sha == head_sha:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"[{ts}] No new commits since {base_sha[:8]} — skipping", flush=True)
        return

    diff = get_diff_since(base_sha)
    if not diff:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"[{ts}] Empty diff ({base_sha[:8]}..{head_sha[:8]}) — skipping", flush=True)
        save_last_checked_sha(head_sha)
        return

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(
        f"[{ts}] Analysing {base_sha[:8]}..{head_sha[:8]}  "
        f"({len(diff)} chars)  agents: {', '.join(AGENTS)}",
        flush=True,
    )

    threads = [
        threading.Thread(
            target=run_agent,
            args=(name, spec, diff, base_sha, head_sha),
            daemon=True,
        )
        for name, spec in AGENTS.items()
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    save_last_checked_sha(head_sha)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tenn code-change monitoring agents")
    parser.add_argument("--once",     action="store_true",
                        help="Run one check and exit")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL,
                        help=f"Poll interval in seconds (default: {POLL_INTERVAL})")
    parser.add_argument("--reset",    action="store_true",
                        help="Clear saved SHA watermark and re-check from HEAD~1")
    args = parser.parse_args()

    if args.reset and STATE_FILE.exists():
        STATE_FILE.unlink()
        print("Watermark cleared — will re-check from HEAD~1.", flush=True)

    # Verify claude CLI is available
    if not shutil.which("claude"):
        print("ERROR: 'claude' CLI not found on PATH.", file=sys.stderr)
        sys.exit(1)

    if args.once:
        check_once()
        return

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{ts}] Monitors started — polling every {args.interval}s  (Ctrl-C to stop)", flush=True)
    print(f"[{ts}] Alerts → {ALERTS_LOG}", flush=True)

    try:
        while True:
            check_once()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"\n[{ts}] Monitors stopped.", flush=True)


if __name__ == "__main__":
    main()
