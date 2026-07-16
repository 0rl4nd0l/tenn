#!/usr/bin/env python3
"""Wait on external work without spending Codex turns on repeated polling.

The supported V1 modes are read-only GitHub PR check observation and attached
execution of a command. A terminal result is written atomically and printed as
one JSON line. A successful wait proves only that the wait condition completed;
it does not prove runtime or extraction functionality.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


SCHEMA_VERSION = "tenn_codex_event_waiter_v1"
SUCCESS_STATES = {"SUCCESS"}
TERMINAL_STATES = {
    "SUCCESS",
    "FAILURE",
    "CANCELLED",
    "TIMEOUT",
    "STALE_TARGET",
    "ERROR",
}
DEFAULT_TIMEOUT_SECONDS = 45 * 60.0
DEFAULT_POLL_SECONDS = 15.0
DEFAULT_MAX_LOG_BYTES = 128 * 1024
MAX_CONSECUTIVE_API_ERRORS = 3


GH_PR_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number
      state
      merged
      isDraft
      headRefOid
      url
      commits(last: 1) {
        nodes {
          commit {
            statusCheckRollup {
              state
              contexts(first: 100) {
                nodes {
                  __typename
                  ... on CheckRun {
                    name
                    status
                    conclusion
                    detailsUrl
                  }
                  ... on StatusContext {
                    context
                    state
                    targetUrl
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
""".strip()


@dataclass(frozen=True)
class GitHubWaitConfig:
    repo: str
    pr_number: int
    expected_head_sha: str
    poll_seconds: float = DEFAULT_POLL_SECONDS
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS


class RollingBytes:
    def __init__(self, limit: int) -> None:
        self.limit = max(int(limit), 1)
        self._value = bytearray()
        self._truncated = False
        self._lock = threading.Lock()

    def append(self, chunk: bytes) -> None:
        if not chunk:
            return
        with self._lock:
            self._value.extend(chunk)
            overflow = len(self._value) - self.limit
            if overflow > 0:
                self._truncated = True
                del self._value[:overflow]

    def value(self) -> bytes:
        with self._lock:
            return bytes(self._value)

    def truncated(self) -> bool:
        with self._lock:
            return self._truncated


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def redact_text(value: str) -> str:
    redacted = re.sub(
        r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+",
        r"\1[REDACTED]",
        value,
    )
    redacted = re.sub(
        r'''(?i)(["']?(?:token|api[_-]?key|password|secret)["']?\s*[:=]\s*)(["'])(?:\\.|(?!\2).)*\2''',
        r"\1\2[REDACTED]\2",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b(token|api[_-]?key|password|secret)(\s*[=:]\s*)[^\s,}\]]+",
        r"\1\2[REDACTED]",
        redacted,
    )
    return re.sub(
        r"\b(?:gh[pousr]_[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]+|sk-[A-Za-z0-9_-]+)\b",
        "[REDACTED]",
        redacted,
    )


def bounded_redacted_log(value: bytes, *, limit: int, truncated: bool) -> str:
    if truncated:
        line_breaks = [index for marker in (b"\n", b"\r") if (index := value.find(marker)) >= 0]
        value = value[min(line_breaks) + 1 :] if line_breaks else b""
    redacted = redact_text(value.decode("utf-8", errors="replace"))
    encoded = redacted.encode("utf-8")
    if len(encoded) > limit:
        encoded = encoded[-limit:]
    return encoded.decode("utf-8", errors="ignore")


def parse_repo(repo: str) -> tuple[str, str]:
    parts = repo.strip().split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("--repo must use OWNER/REPO form")
    return parts[0], parts[1]


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def build_terminal_result(
    *,
    kind: str,
    state: str,
    started_at: str,
    target: dict[str, Any],
    observed: dict[str, Any],
    summary: str,
    evidence: dict[str, Any] | None = None,
    wait_id: str | None = None,
) -> dict[str, Any]:
    if state not in TERMINAL_STATES:
        raise ValueError(f"unsupported terminal state: {state}")
    return {
        "schema_version": SCHEMA_VERSION,
        "wait_id": wait_id or str(uuid.uuid4()),
        "kind": kind,
        "state": state,
        "started_at": started_at,
        "finished_at": utc_now(),
        "target": target,
        "observed": observed,
        "summary": summary,
        "evidence": dict(evidence or {}),
        "functionality_proven": False,
    }


def write_and_emit(payload: dict[str, Any], output_path: Path) -> None:
    evidence = payload.setdefault("evidence", {})
    evidence.setdefault("result_path", str(output_path))
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _atomic_write_text(output_path, serialized + "\n")
    print(serialized, flush=True)


def fetch_github_pr_snapshot(repo: str, pr_number: int) -> dict[str, Any]:
    owner, name = parse_repo(repo)
    completed = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={GH_PR_QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"number={pr_number}",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        detail = redact_text(completed.stderr.strip() or completed.stdout.strip())
        raise RuntimeError(f"gh api graphql failed: {detail or 'unknown error'}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("gh api graphql returned invalid JSON") from exc
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL errors: {redact_text(json.dumps(payload['errors']))}")

    repository = (payload.get("data") or {}).get("repository")
    pull_request = repository.get("pullRequest") if isinstance(repository, dict) else None
    if not isinstance(pull_request, dict):
        raise RuntimeError(f"pull request {repo}#{pr_number} was not found")

    commit_nodes = ((pull_request.get("commits") or {}).get("nodes") or [])
    commit = {}
    if commit_nodes and isinstance(commit_nodes[-1], dict):
        commit = commit_nodes[-1].get("commit") or {}
    rollup = commit.get("statusCheckRollup") if isinstance(commit, dict) else None
    context_nodes = []
    if isinstance(rollup, dict):
        context_nodes = ((rollup.get("contexts") or {}).get("nodes") or [])

    contexts: list[dict[str, Any]] = []
    for raw in context_nodes:
        if not isinstance(raw, dict):
            continue
        kind = raw.get("__typename")
        if kind == "CheckRun":
            status = str(raw.get("status") or "UNKNOWN").upper()
            conclusion = str(raw.get("conclusion") or "").upper()
            contexts.append(
                {
                    "kind": "check_run",
                    "name": str(raw.get("name") or "unnamed"),
                    "state": conclusion if status == "COMPLETED" and conclusion else status,
                }
            )
        elif kind == "StatusContext":
            contexts.append(
                {
                    "kind": "status_context",
                    "name": str(raw.get("context") or "unnamed"),
                    "state": str(raw.get("state") or "UNKNOWN").upper(),
                }
            )
    contexts.sort(key=lambda item: (str(item["kind"]), str(item["name"])))
    return {
        "head_sha": str(pull_request.get("headRefOid") or ""),
        "pr_state": str(pull_request.get("state") or "UNKNOWN").upper(),
        "merged": bool(pull_request.get("merged")),
        "is_draft": bool(pull_request.get("isDraft")),
        "rollup_state": (
            str(rollup.get("state") or "").upper() if isinstance(rollup, dict) else None
        ),
        "contexts": contexts,
        "url": str(pull_request.get("url") or ""),
    }


def _snapshot_fingerprint(snapshot: dict[str, Any]) -> str:
    relevant = {
        "head_sha": snapshot.get("head_sha"),
        "pr_state": snapshot.get("pr_state"),
        "merged": snapshot.get("merged"),
        "rollup_state": snapshot.get("rollup_state"),
        "contexts": snapshot.get("contexts") or [],
    }
    return json.dumps(relevant, sort_keys=True, separators=(",", ":"))


def _github_partial_result(
    *,
    config: GitHubWaitConfig,
    state: str,
    observed: dict[str, Any],
    summary: str,
) -> dict[str, Any]:
    return {
        "state": state,
        "target": {
            "repo": config.repo,
            "pr_number": config.pr_number,
            "expected_head_sha": config.expected_head_sha,
        },
        "observed": observed,
        "summary": summary,
    }


def wait_for_github_pr(
    config: GitHubWaitConfig,
    *,
    fetch_snapshot: Callable[[str, int], dict[str, Any]] = fetch_github_pr_snapshot,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    parse_repo(config.repo)
    if config.pr_number <= 0:
        raise ValueError("--pr must be positive")
    if not config.expected_head_sha.strip():
        raise ValueError("--head-sha must not be empty")
    if config.poll_seconds <= 0 or config.timeout_seconds <= 0:
        raise ValueError("poll and timeout values must be positive")

    deadline = monotonic() + config.timeout_seconds
    polls = 0
    consecutive_api_errors = 0
    stable_terminal_snapshots = 0
    terminal_fingerprint: str | None = None
    last_snapshot: dict[str, Any] | None = None
    last_error: str | None = None

    while True:
        polls += 1
        try:
            current = fetch_snapshot(config.repo, config.pr_number)
            consecutive_api_errors = 0
            last_error = None
            last_snapshot = current
        except Exception as exc:  # external command/network boundary
            consecutive_api_errors += 1
            last_error = redact_text(str(exc))
            if consecutive_api_errors >= MAX_CONSECUTIVE_API_ERRORS:
                return _github_partial_result(
                    config=config,
                    state="ERROR",
                    observed={
                        "poll_count": polls,
                        "consecutive_api_errors": consecutive_api_errors,
                        "last_error": last_error,
                    },
                    summary="GitHub status could not be read after repeated errors",
                )
            if monotonic() >= deadline:
                break
            sleep(min(config.poll_seconds, max(deadline - monotonic(), 0.0)))
            continue

        observed = dict(current)
        observed["poll_count"] = polls
        observed["consecutive_api_errors"] = consecutive_api_errors

        if str(current.get("head_sha") or "") != config.expected_head_sha:
            return _github_partial_result(
                config=config,
                state="STALE_TARGET",
                observed=observed,
                summary="PR head changed while waiting; live state must be re-evaluated",
            )
        if bool(current.get("merged")) or str(current.get("pr_state")).upper() == "MERGED":
            observed["outcome"] = "merged"
            return _github_partial_result(
                config=config,
                state="SUCCESS",
                observed=observed,
                summary="PR was merged while the waiter was active",
            )
        if str(current.get("pr_state")).upper() == "CLOSED":
            observed["outcome"] = "closed_unmerged"
            return _github_partial_result(
                config=config,
                state="CANCELLED",
                observed=observed,
                summary="PR closed without merge while the waiter was active",
            )

        rollup_state = str(current.get("rollup_state") or "").upper()
        if rollup_state in {"FAILURE", "ERROR"}:
            observed["outcome"] = "checks_failed"
            return _github_partial_result(
                config=config,
                state="FAILURE",
                observed=observed,
                summary=f"GitHub check rollup reached {rollup_state}",
            )
        if rollup_state == "SUCCESS":
            fingerprint = _snapshot_fingerprint(current)
            if fingerprint == terminal_fingerprint:
                stable_terminal_snapshots += 1
            else:
                terminal_fingerprint = fingerprint
                stable_terminal_snapshots = 1
            if stable_terminal_snapshots >= 2:
                observed["outcome"] = "checks_succeeded"
                observed["stable_terminal_snapshots"] = stable_terminal_snapshots
                return _github_partial_result(
                    config=config,
                    state="SUCCESS",
                    observed=observed,
                    summary="GitHub check rollup was stable and successful",
                )
        else:
            terminal_fingerprint = None
            stable_terminal_snapshots = 0

        if monotonic() >= deadline:
            break
        sleep(min(config.poll_seconds, max(deadline - monotonic(), 0.0)))

    observed = dict(last_snapshot or {})
    observed.update(
        {
            "poll_count": polls,
            "consecutive_api_errors": consecutive_api_errors,
            "last_error": last_error,
        }
    )
    return _github_partial_result(
        config=config,
        state="TIMEOUT",
        observed=observed,
        summary="GitHub check wait reached its timeout",
    )


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        process_group = process.pid

        def group_exists() -> bool:
            try:
                os.killpg(process_group, 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
            return True

        try:
            os.killpg(process_group, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 2.0
        while group_exists() and time.monotonic() < deadline:
            process.poll()
            time.sleep(0.05)
        if group_exists():
            try:
                os.killpg(process_group, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process_group, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)
        return

    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def run_command_wait(
    command: Sequence[str],
    *,
    timeout_seconds: float,
    max_log_bytes: int,
    output_path: Path,
) -> dict[str, Any]:
    argv = list(command)
    if not argv:
        raise ValueError("command mode requires arguments after --")
    if timeout_seconds <= 0 or max_log_bytes <= 0:
        raise ValueError("timeout and max-log-bytes must be positive")

    started_at = utc_now()
    started_monotonic = time.monotonic()
    log_path = Path(f"{output_path}.log")
    rolling = RollingBytes(max_log_bytes)
    process: subprocess.Popen[bytes] | None = None
    reader: threading.Thread | None = None
    termination_attempted = False

    try:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        assert process.stdout is not None

        def read_output() -> None:
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                rolling.append(chunk)

        reader = threading.Thread(target=read_output, name="codex-waiter-output", daemon=True)
        reader.start()
        try:
            exit_code = process.wait(timeout=timeout_seconds)
            state = "SUCCESS" if exit_code == 0 else "FAILURE"
            summary = (
                "command completed successfully"
                if exit_code == 0
                else f"command exited with status {exit_code}"
            )
        except subprocess.TimeoutExpired:
            termination_attempted = True
            _terminate_process_group(process)
            exit_code = process.returncode
            state = "TIMEOUT"
            summary = "command exceeded its timeout and was terminated"
    except KeyboardInterrupt:
        if process is not None and process.poll() is None:
            termination_attempted = True
            _terminate_process_group(process)
        exit_code = process.returncode if process is not None else None
        state = "CANCELLED"
        summary = "command wait was interrupted and its process group was terminated"
    except FileNotFoundError as exc:
        exit_code = None
        state = "ERROR"
        summary = f"command executable was not found: {redact_text(str(exc))}"
    except Exception as exc:
        if process is not None and process.poll() is None:
            termination_attempted = True
            _terminate_process_group(process)
        exit_code = process.returncode if process is not None else None
        state = "ERROR"
        summary = f"command wait failed: {redact_text(str(exc))}"
    finally:
        if reader is not None:
            reader.join(timeout=2)
        if process is not None and process.stdout is not None:
            process.stdout.close()

    log_text = bounded_redacted_log(
        rolling.value(),
        limit=max_log_bytes,
        truncated=rolling.truncated(),
    )
    _atomic_write_text(log_path, log_text)
    duration_seconds = round(time.monotonic() - started_monotonic, 3)
    return build_terminal_result(
        kind="command",
        state=state,
        started_at=started_at,
        target={"executable": argv[0], "arg_count": len(argv)},
        observed={
            "exit_code": exit_code,
            "duration_seconds": duration_seconds,
            "termination_attempted": termination_attempted,
            "captured_log_bytes": len(log_text.encode("utf-8")),
        },
        summary=summary,
        evidence={"log_path": str(log_path)},
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wait on GitHub checks or a command without model polling."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    github = subparsers.add_parser("github-pr", help="wait for a PR check rollup")
    github.add_argument("--repo", required=True, help="repository in OWNER/REPO form")
    github.add_argument("--pr", required=True, type=int, dest="pr_number")
    github.add_argument("--head-sha", required=True, dest="expected_head_sha")
    github.add_argument("--output", required=True, type=Path)
    github.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    github.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)

    command = subparsers.add_parser("command", help="run and wait for an argv")
    command.add_argument("--output", required=True, type=Path)
    command.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    command.add_argument("--max-log-bytes", type=int, default=DEFAULT_MAX_LOG_BYTES)
    command.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_path: Path = args.output
    started_at = utc_now()
    try:
        if args.mode == "github-pr":
            config = GitHubWaitConfig(
                repo=args.repo,
                pr_number=args.pr_number,
                expected_head_sha=args.expected_head_sha,
                poll_seconds=args.poll_seconds,
                timeout_seconds=args.timeout_seconds,
            )
            partial = wait_for_github_pr(config)
            payload = build_terminal_result(
                kind="github_pr",
                state=str(partial["state"]),
                started_at=started_at,
                target=partial["target"],
                observed=partial["observed"],
                summary=str(partial["summary"]),
            )
        else:
            command = list(args.command)
            if command and command[0] == "--":
                command = command[1:]
            payload = run_command_wait(
                command,
                timeout_seconds=args.timeout_seconds,
                max_log_bytes=args.max_log_bytes,
                output_path=output_path,
            )
    except Exception as exc:
        payload = build_terminal_result(
            kind="github_pr" if args.mode == "github-pr" else "command",
            state="ERROR",
            started_at=started_at,
            target={},
            observed={"error": redact_text(str(exc))},
            summary="waiter configuration or execution failed",
        )
    write_and_emit(payload, output_path)
    return 0 if payload["state"] in SUCCESS_STATES else 1


if __name__ == "__main__":
    raise SystemExit(main())
