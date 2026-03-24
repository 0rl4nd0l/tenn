#!/usr/bin/env python3
"""
Export the current Claude Code session to a readable text file for orchestrator use.
Includes conversation turns, tool calls/results, and project context.

Usage: python3 save-chat.py [output_dir] [session_jsonl_path]
"""

import json
import os
import pwd
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOL_RESULT_PREVIEW = 300   # max chars of tool output to show inline
TOOL_INPUT_PREVIEW  = 200   # max chars of long tool inputs
CLAUDE_MD_MAX_LINES = 40    # first N lines of CLAUDE.md (already in context for the agent)
CONVERSATION_TURNS  = 25    # only include the last N turns (keeps export focused on recent work)
TEXT_ITEM_MAX_LINES = 30    # cap long text items (task notifications, agent reports) to this many lines
COCKPIT_EXPORT_PATH = Path("reports") / "cockpit" / "exports" / "claude_context.json"


# ---------------------------------------------------------------------------
# Session / project helpers
# ---------------------------------------------------------------------------

def _candidate_claude_homes(cwd: str) -> list[Path]:
    candidates: list[Path] = []

    env_home = str(os.environ.get("CLAUDE_HOME") or "").strip()
    if env_home:
        candidates.append(Path(env_home).expanduser())

    real_home = pwd.getpwuid(os.getuid()).pw_dir
    if real_home:
        candidates.append(Path(real_home) / ".claude")

    candidates.append(Path.home() / ".claude")

    cwd_path = Path(cwd).resolve()
    for parent in [cwd_path, *cwd_path.parents]:
        maybe_home = parent / ".claude"
        candidates.append(maybe_home)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _resolve_claude_projects_root(cwd: str) -> Path:
    for base in _candidate_claude_homes(cwd):
        projects = base / "projects"
        if projects.exists():
            return projects
    return _candidate_claude_homes(cwd)[0] / "projects"


def get_project_dir(cwd: str) -> Path:
    slug = cwd.replace("/", "-").replace(".", "-").replace("_", "-")
    if slug.startswith("-"):
        slug = slug[1:]
    return _resolve_claude_projects_root(cwd) / f"-{slug}"


def find_session_file(project_dir: Path) -> Path | None:
    env_session = str(os.environ.get("CLAUDE_SESSION_FILE") or "").strip()
    if env_session:
        path = Path(env_session).expanduser()
        if path.exists():
            return path

    try:
        jsonls = [p for p in project_dir.rglob("*.jsonl") if p.is_file()]
    except PermissionError:
        raise

    if not jsonls:
        return None
    return max(jsonls, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _fmt_tool_input(name: str, inp: dict) -> str:
    """Return a compact one-liner showing the most relevant part of a tool call."""
    if name == "Bash":
        cmd = inp.get("command", "")
        # Show first line of the command
        first_line = cmd.split("\n")[0]
        rest = cmd[len(first_line):]
        if rest.strip():
            first_line += " ..."
        return f'Bash({first_line!r})'
    if name in ("Read", "Glob", "Grep"):
        path = inp.get("file_path") or inp.get("pattern") or inp.get("path") or ""
        extra = ""
        if name == "Grep":
            extra = f', {inp.get("pattern", "")!r}'
        return f'{name}({path!r}{extra})'
    if name in ("Edit", "Write"):
        path = inp.get("file_path", "")
        return f'{name}({path!r})'
    if name == "Agent":
        desc = inp.get("description", inp.get("prompt", ""))[:60]
        return f'Agent({desc!r})'
    if name == "TodoWrite":
        return "TodoWrite(...)"
    # Generic fallback
    raw = json.dumps(inp, ensure_ascii=False)
    if len(raw) > TOOL_INPUT_PREVIEW:
        raw = raw[:TOOL_INPUT_PREVIEW] + " ..."
    return f'{name}({raw})'


def _fmt_tool_result(content) -> str:
    """Return a preview of a tool result."""
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                texts.append(block.get("text", "") or block.get("content", ""))
            else:
                texts.append(str(block))
        text = "\n".join(t for t in texts if t)
    elif isinstance(content, str):
        text = content
    else:
        text = json.dumps(content, ensure_ascii=False)

    text = text.strip()
    if len(text) > TOOL_RESULT_PREVIEW:
        text = text[:TOOL_RESULT_PREVIEW] + f"\n  ... [{len(text)} chars total]"
    return text


def parse_session(jsonl_path: Path) -> list[dict]:
    """
    Parse a session JSONL into an ordered list of turn dicts:
      {role, timestamp, items: [{type: "text"|"tool_call"|"tool_result", ...}]}

    tool_use blocks from assistant messages are paired with their tool_result
    from subsequent user messages using the tool_use_id.
    """
    raw_records = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("type") in ("user", "assistant"):
                raw_records.append(r)

    # Build a map of tool_use_id -> tool_result content
    tool_results: dict[str, dict] = {}
    for rec in raw_records:
        if rec["type"] != "user":
            continue
        content = rec.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_result":
                tid = block.get("tool_use_id", "")
                tool_results[tid] = {
                    "content": block.get("content", ""),
                    "is_error": block.get("is_error", False),
                }

    # Now build the turn list
    turns = []
    for rec in raw_records:
        role = rec["type"]
        ts = rec.get("timestamp", "")
        content = rec.get("message", {}).get("content", [])

        if isinstance(content, str):
            # Plain string user message
            if content.strip():
                turns.append({"role": role, "timestamp": ts,
                               "items": [{"type": "text", "text": content.strip()}]})
            continue

        if not isinstance(content, list):
            continue

        items = []
        for block in content:
            btype = block.get("type", "")

            if btype == "text":
                text = block.get("text", "").strip()
                if text:
                    items.append({"type": "text", "text": text})

            elif btype == "tool_use":
                tid = block.get("id", "")
                name = block.get("name", "")
                inp = block.get("input", {})
                call_str = _fmt_tool_input(name, inp)
                result = tool_results.get(tid)
                items.append({
                    "type": "tool_call",
                    "call": call_str,
                    "tool_name": name,
                    "result": result,
                })

            elif btype == "tool_result":
                # Skip — already absorbed into tool_call items above
                pass

            elif btype == "thinking":
                # Skip thinking blocks from export
                pass

        # User messages that contain only tool_results are already handled above; skip.
        if role == "user" and all(b.get("type") == "tool_result" for b in content):
            continue

        if items:
            turns.append({"role": role, "timestamp": ts, "items": items})

    return turns


# ---------------------------------------------------------------------------
# Context gathering
# ---------------------------------------------------------------------------

def run(cmd: str, cwd: str | None = None) -> str:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10,
            cwd=cwd or os.getcwd()
        )
        return result.stdout.strip()
    except Exception:
        return ""


def gather_git_context(repo_root: str) -> str:
    branch    = run("git rev-parse --abbrev-ref HEAD", repo_root)
    log       = run("git log --oneline -15", repo_root)
    status    = run("git status --short", repo_root)
    worktrees = run("git worktree list", repo_root)

    lines = []
    if branch:
        lines.append(f"Branch: {branch}")
    if worktrees:
        lines.append(f"\nActive worktrees:\n{worktrees}")
    lines.append(f"\nUncommitted changes:\n{status}" if status else "\nWorking tree: clean")
    if log:
        lines.append(f"\nRecent commits (last 15):\n{log}")
    return "\n".join(lines)


def gather_claude_md(repo_root: str) -> str:
    path = Path(repo_root) / "CLAUDE.md"
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    truncated = lines[:CLAUDE_MD_MAX_LINES]
    if len(lines) > CLAUDE_MD_MAX_LINES:
        truncated.append(f"\n... [{len(lines) - CLAUDE_MD_MAX_LINES} more lines — see CLAUDE.md]")
    return "\n".join(truncated)


def gather_memory_files(project_dir: Path) -> str:
    global_memory = project_dir.parent / "memory"
    blocks = []
    for mdir in [global_memory, project_dir / "memory"]:
        if not mdir.exists():
            continue
        try:
            files = sorted(mdir.glob("*.md"))
        except Exception:
            continue
        for mfile in files:
            if mfile.name == "MEMORY.md":
                continue
            try:
                content = mfile.read_text(encoding="utf-8").strip()
                if content:
                    blocks.append(f"[{mfile.name}]\n{content}")
            except Exception:
                pass
    return "\n\n".join(blocks)


def gather_cockpit_export(repo_root: str) -> str:
    path = (Path(repo_root) / COCKPIT_EXPORT_PATH).resolve()
    if not path.exists() or not path.is_file():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"Failed to parse {path}: {exc}"
    return json.dumps(payload, indent=2, default=str)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def section(title: str, body: str) -> str:
    bar = "=" * 60
    return f"{bar}\n{title}\n{bar}\n\n{body}\n"


def format_export(
    turns: list[dict],
    session_path: Path | None,
    git_ctx: str,
    claude_md: str,
    memory: str,
    cockpit_export: str,
    cwd: str,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    session_label = session_path.stem if session_path is not None else "cockpit_export_only"

    parts = []
    parts.append(
        f"CLAUDE CODE SESSION EXPORT\n"
        f"Generated : {now}\n"
        f"Session   : {session_label}\n"
        f"Project   : {cwd}\n"
    )

    if git_ctx:
        parts.append(section("GIT CONTEXT", git_ctx))
    if memory:
        parts.append(section("AGENT MEMORY", memory))
    if claude_md:
        parts.append(section("CLAUDE.md (PROJECT INSTRUCTIONS)", claude_md))
    if cockpit_export:
        parts.append(section("COCKPIT EXPORT", cockpit_export))

    conv_lines = []
    if turns:
        visible_turns = turns[-CONVERSATION_TURNS:] if len(turns) > CONVERSATION_TURNS else turns
        if len(visible_turns) < len(turns):
            conv_lines.insert(0, f"[... {len(turns) - len(visible_turns)} earlier turns omitted — use full session file for complete history]\n")

        for turn in visible_turns:
            role_label = "USER" if turn["role"] == "user" else "CLAUDE"
            ts = ""
            if turn.get("timestamp"):
                try:
                    dt = datetime.fromisoformat(turn["timestamp"].replace("Z", "+00:00"))
                    ts = f"  [{dt.strftime('%H:%M')}]"
                except Exception:
                    pass

            conv_lines.append(f"--- {role_label}{ts} ---")

            for item in turn["items"]:
                if item["type"] == "text":
                    text = item["text"]
                    lines = text.splitlines()
                    if len(lines) > TEXT_ITEM_MAX_LINES:
                        text = "\n".join(lines[:TEXT_ITEM_MAX_LINES]) + f"\n  ... [{len(lines) - TEXT_ITEM_MAX_LINES} more lines]"
                    conv_lines.append(text)

                elif item["type"] == "tool_call":
                    conv_lines.append(f"\n  > {item['call']}")
                    result = item.get("result")
                    if result is not None:
                        is_err = result.get("is_error", False)
                        out = _fmt_tool_result(result.get("content", ""))
                        prefix = "  ERR" if is_err else "  <"
                        if out:
                            indented = "\n".join(f"    {l}" for l in out.splitlines())
                            conv_lines.append(f"{prefix}\n{indented}")
                        else:
                            conv_lines.append(f"{prefix} (no output)")

            conv_lines.append("")
    else:
        conv_lines.append("No Claude session transcript was readable. Cockpit export data is included above when available.")

    parts.append(section("CONVERSATION", "\n".join(conv_lines)))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cwd = os.environ.get("PWD", os.getcwd())
    session_file: Path | None = None

    if len(sys.argv) > 1 and not Path(sys.argv[1]).is_dir():
        session_file = Path(sys.argv[1])
        project_dir = get_project_dir(cwd)
    else:
        project_dir = get_project_dir(cwd)
        if not project_dir.exists():
            print(f"No Claude project directory found at {project_dir}", file=sys.stderr)
            sys.exit(1)
        try:
            session_file = find_session_file(project_dir)
        except PermissionError:
            print(
                "Claude project directory exists but is not readable. "
                "Set CLAUDE_SESSION_FILE to the active session JSONL path and rerun.",
                file=sys.stderr,
            )
            session_file = None

    repo_root = run("git rev-parse --show-toplevel", cwd) or cwd
    cockpit_export = gather_cockpit_export(repo_root)

    turns: list[dict] = []
    if session_file is not None:
        turns = parse_session(session_file)
    if session_file is None and not cockpit_export:
        print(
            "No session files found. If Claude stores sessions outside the default project root, "
            "set CLAUDE_SESSION_FILE to the active session JSONL path and rerun.",
            file=sys.stderr,
        )
        sys.exit(1)
    if session_file is not None and not turns and not cockpit_export:
        print("No readable conversation turns found.", file=sys.stderr)
        sys.exit(1)

    git_ctx   = gather_git_context(repo_root)
    claude_md = gather_claude_md(repo_root)
    memory    = gather_memory_files(project_dir)

    export_text = format_export(turns, session_file, git_ctx, claude_md, memory, cockpit_export, cwd)

    print(export_text)


if __name__ == "__main__":
    main()
