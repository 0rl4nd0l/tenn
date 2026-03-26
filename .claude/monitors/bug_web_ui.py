#!/usr/bin/env python3
"""
Bug Monitor Web UI
==================
Reads .claude/monitors/alerts.log and presents a dashboard with:
  - All detected bugs/issues grouped by type and severity
  - Per-bug explanation panel
  - Agent debate (two fix proposals + synthesised recommendation)
  - "Deploy Fix" button that applies the winning proposal via git patch

Run:
  /home/l4nd0/tenn/financial-engine_v2/.venv/bin/python .claude/monitors/bug_web_ui.py
  Open: http://localhost:8765
"""

import hashlib, json, os, re, shutil, socketserver, subprocess, textwrap, threading, time, uuid
from pathlib import Path
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import psutil

# Extraction workbench (same directory)
from extraction_workbench import (
    list_fixtures as wb_list_fixtures,
    load_fixture as wb_load_fixture,
    resolve_pdf_path as wb_resolve_pdf,
    start_extraction_job as wb_start_job,
    get_job as wb_get_job,
    list_jobs as wb_list_jobs,
    cancel_job as wb_cancel_job,
    get_history as wb_get_history,
    retry_metric as wb_retry_metric,
    start_chat as wb_start_chat,
    send_chat_message as wb_send_chat,
    get_chat as wb_get_chat,
    list_tickers as wb_list_tickers,
    list_available_pdfs as wb_list_pdfs,
    FE_ROOT as WB_FE_ROOT,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parents[2]
LOG_FILE   = Path(__file__).parent / "alerts.log"
DEBATES_DB = Path(__file__).parent / "debates.json"
PORT       = 8765

REGISTRY_DB = Path(__file__).parent / "bug_registry.json"

JOBS: dict[str, dict] = {}
_JOBS_LOCK    = threading.Lock()
_DEBATES_LOCK = threading.Lock()
_REGISTRY_LOCK = threading.Lock()

# ── Monitor scan state ───────────────────────────────────────────────────────
_SCAN_STATE = {"running": False, "status": "idle", "done": True}
_SCAN_LOCK = threading.Lock()

MONITOR_SCRIPT = Path(__file__).parent / "monitor_agents.py"


def _run_monitor_scan():
    """Run monitor_agents.py --once in a subprocess."""
    with _SCAN_LOCK:
        _SCAN_STATE["running"] = True
        _SCAN_STATE["done"] = False
        _SCAN_STATE["status"] = "Starting scan..."

    try:
        venv_python = str(REPO_ROOT / "financial-engine_v2" / ".venv" / "bin" / "python")
        proc = subprocess.Popen(
            [venv_python, str(MONITOR_SCRIPT), "--once"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=str(REPO_ROOT),
        )
        lines = []
        for line in proc.stdout:
            line = line.rstrip()
            lines.append(line)
            # Update status with last meaningful line
            if line.strip():
                with _SCAN_LOCK:
                    _SCAN_STATE["status"] = line[-120:]

        proc.wait(timeout=300)

        with _SCAN_LOCK:
            if proc.returncode == 0:
                _SCAN_STATE["status"] = f"Scan complete — {len(lines)} log lines"
            else:
                _SCAN_STATE["status"] = f"Scan failed (rc={proc.returncode})"

    except Exception as e:
        with _SCAN_LOCK:
            _SCAN_STATE["status"] = f"Error: {e}"
    finally:
        with _SCAN_LOCK:
            _SCAN_STATE["running"] = False
            _SCAN_STATE["done"] = True

# ── Global drawer chat sessions ──────────────────────────────────────────────
_DRAWER_CHATS: dict[str, dict] = {}
_DRAWER_LOCK = threading.Lock()


def _clean_claude_output(raw: str) -> str:
    """Strip ANSI codes, TUI chrome, and Claude CLI artifacts from script log output."""
    import re
    clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw)
    clean = re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)', '', clean)
    clean = re.sub(r'\x1b\[\?[0-9;]*[a-zA-Z]', '', clean)
    clean = re.sub(r'\x1b[>=<][^\n]*', '', clean)
    clean = re.sub(r'\x1b\([AB0-9]', '', clean)
    clean = re.sub(r'\r', '', clean)
    # Box drawing and spinner characters
    clean = re.sub(r'[╭╮╰╯│─┌┐└┘├┤┬┴┼▐▛▜▝▘█▌▍▎▏⎿✶✻✽✢●◐⏵]', '', clean)

    skip_patterns = [
        'Claude Code v', 'Sonnet 4', 'Claude Max', '~/tenn',
        'bypass permissions', 'shift+tab', 'ctrl+', 'esc to interrupt',
        'Gusting', 'Crunching', 'Reading ', 'Stop says:', 'Stop hook',
        'SessionStart:', 'MILESTONE NOT', 'MEMORY CHECK', 'FEEDBACK:',
        'SESSION MEMORY', 'hook error', 'ACTIVE FEEDBACK', 'RELEVANT MEMORIES',
        'Recent activity', 'Welcome back', '/resume for more', "What's new",
        'Added `', 'release-notes', 'Organization', 'Ran ', 'Permission denied',
        'medium  /effort', 'ctrl+g to', 'ctrl+o to',
    ]
    lines = []
    for l in clean.split("\n"):
        stripped = l.strip()
        if not stripped or len(stripped) < 2:
            continue
        if any(p in stripped for p in skip_patterns):
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


def _start_drawer_chat(page_context: str, message: str, screenshot_path: str | None) -> dict:
    """Start an interactive claude session in tmux, bridged to the web UI."""
    import shutil
    chat_id = f"drawer_{int(time.time())}"
    tmux_session = f"chat-{chat_id[-8:]}"

    log_dir = REPO_ROOT / ".claude" / "monitors" / "chat_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    output_log = log_dir / f"{chat_id}.log"
    output_log.write_text("")

    if not shutil.which("tmux"):
        return {"ok": False, "error": "tmux not installed — run: sudo apt install tmux"}

    # Start interactive claude in tmux with script logging
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", tmux_session, "-x", "200", "-y", "50",
         "bash", "-c", f'script -q -f {output_log} -c "claude --model sonnet"; sleep 5'],
        cwd=str(REPO_ROOT),
    )

    with _DRAWER_LOCK:
        _DRAWER_CHATS[chat_id] = {
            "page_context": page_context,
            "messages": [],
            "status": "thinking",
            "_tmux": tmux_session,
            "_log": str(output_log),
            "_log_pos": 0,
        }

    # Wait for claude to start, then send initial message
    def _init():
        time.sleep(4)  # let claude boot
        full_msg = page_context or ""
        if screenshot_path:
            full_msg += f"\n\nScreenshot of what I see: {screenshot_path}"
        full_msg += f"\n\n{message}"
        _tmux_send(tmux_session, full_msg)
        _wait_for_response(chat_id, message)

    threading.Thread(target=_init, daemon=True).start()
    return {"ok": True, "chat_id": chat_id, "tmux_session": tmux_session}


def _tmux_send(session: str, message: str) -> None:
    """Send a message to a tmux session via send-keys."""
    # For multi-line, write to a temp file and use load-buffer + paste
    if "\n" in message and len(message) > 200:
        tmp = REPO_ROOT / ".claude" / "monitors" / "chat_logs" / "_tmux_buf.txt"
        tmp.write_text(message)
        subprocess.run(["tmux", "load-buffer", str(tmp)], timeout=5)
        subprocess.run(["tmux", "paste-buffer", "-t", session], timeout=5)
    else:
        # Single line — escape special chars and send
        for line in message.split("\n"):
            subprocess.run(
                ["tmux", "send-keys", "-t", session, "-l", line],
                timeout=5,
            )
            subprocess.run(["tmux", "send-keys", "-t", session, "Enter"], timeout=5)
            time.sleep(0.1)
    # Final Enter to submit
    subprocess.run(["tmux", "send-keys", "-t", session, "Enter"], timeout=5)


def _wait_for_response(chat_id: str, user_msg: str) -> None:
    """Tail the script log until Claude finishes responding."""
    import re
    with _DRAWER_LOCK:
        chat = _DRAWER_CHATS.get(chat_id)
        if not chat:
            return
        chat["messages"].append({"role": "user", "text": user_msg})
        log_path = Path(chat["_log"])
        start_pos = chat["_log_pos"]

    start_time = time.time()
    stable_count = 0
    last_size = start_pos
    collected = []

    while time.time() - start_time < 180:
        time.sleep(2)
        try:
            current_size = log_path.stat().st_size
        except Exception:
            continue

        if current_size > last_size:
            with open(log_path, "r", errors="replace") as f:
                f.seek(last_size)
                new_text = f.read()
            last_size = current_size
            collected.append(new_text)
            stable_count = 0
        else:
            stable_count += 1
            # 3 polls (6s) of no new output after some content = done
            if stable_count >= 3 and collected:
                break

    raw = "".join(collected)
    response = _clean_claude_output(raw)
    if not response:
        response = "(response in terminal — run: tmux attach -t " + chat.get("_tmux", "?") + ")"

    with _DRAWER_LOCK:
        chat = _DRAWER_CHATS.get(chat_id)
        if chat:
            chat["messages"].append({"role": "assistant", "text": response})
            chat["status"] = "ready"
            chat["_log_pos"] = last_size


def _send_drawer_chat(chat_id: str, message: str) -> dict:
    """Send a follow-up message to the tmux claude session."""
    with _DRAWER_LOCK:
        chat = _DRAWER_CHATS.get(chat_id)
    if not chat:
        return {"ok": False, "error": "Chat not found"}
    if chat["status"] == "thinking":
        return {"ok": False, "error": "Already processing"}

    tmux_session = chat.get("_tmux")
    if not tmux_session:
        return {"ok": False, "error": "No tmux session"}

    # Check tmux session is still alive
    check = subprocess.run(["tmux", "has-session", "-t", tmux_session],
                           capture_output=True, timeout=5)
    if check.returncode != 0:
        return {"ok": False, "error": "tmux session ended — start a new chat"}

    with _DRAWER_LOCK:
        chat["status"] = "thinking"
        chat["_log_pos"] = Path(chat["_log"]).stat().st_size  # mark current position

    def _run():
        _tmux_send(tmux_session, message)
        _wait_for_response(chat_id, message)

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True}

# ── Service health probes ─────────────────────────────────────────────────────
import urllib.request, urllib.error

SERVICE_CHECKS = [
    {"name": "Backend API",   "url": "http://127.0.0.1:8000/api/health",  "port": 8000, "icon": "⚡"},
    {"name": "llama.cpp",     "url": "http://127.0.0.1:8001/health",      "port": 8001, "icon": "🧠"},
    {"name": "PostgreSQL",    "port": 5432, "icon": "🐘"},
    {"name": "Redis",         "port": 6379, "icon": "📦"},
    {"name": "Qdrant",        "url": "http://127.0.0.1:6333/",             "port": 6333, "icon": "🔍"},
    {"name": "Ollama",        "url": "http://127.0.0.1:11434/api/tags",   "port": 11434, "icon": "🦙"},
]


def _probe_service(svc: dict) -> dict:
    """Probe a single service; return dict with name, status, latency_ms, detail."""
    import socket, time as _t
    result = {"name": svc["name"], "port": svc["port"], "icon": svc.get("icon", "")}
    url = svc.get("url")
    start = _t.monotonic()
    try:
        if url:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                body = resp.read(512).decode("utf-8", errors="replace")
                result["status"] = "up"
                result["detail"] = body[:120]
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", svc["port"]))
            s.close()
            result["status"] = "up"
            result["detail"] = f"TCP port {svc['port']} open"
        result["latency_ms"] = round((_t.monotonic() - start) * 1000)
    except Exception as exc:
        result["status"] = "down"
        result["detail"] = str(exc)[:120]
        result["latency_ms"] = None
    return result


def _probe_all_services() -> list[dict]:
    """Probe all services in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = []
    with ThreadPoolExecutor(max_workers=len(SERVICE_CHECKS)) as ex:
        futs = {ex.submit(_probe_service, s): s for s in SERVICE_CHECKS}
        for f in as_completed(futs):
            results.append(f.result())
    results.sort(key=lambda r: r["port"])
    return results


def _get_git_status() -> dict:
    """Return branch, last commit, and uncommitted file count."""
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=10, cwd=str(REPO_ROOT),
        ).stdout.strip()
        last_commit = subprocess.run(
            ["git", "log", "-1", "--format=%h %s (%ar)"],
            capture_output=True, text=True, timeout=10, cwd=str(REPO_ROOT),
        ).stdout.strip()
        # Use --porcelain for speed; avoid -u which can be slow on large repos
        status = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=10, cwd=str(REPO_ROOT),
        ).stdout.strip()
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--directory"],
            capture_output=True, text=True, timeout=10, cwd=str(REPO_ROOT),
        ).stdout.strip()
        dirty = len([l for l in (status + "\n" + untracked).splitlines() if l.strip()])
        return {"branch": branch, "last_commit": last_commit, "dirty_files": dirty}
    except Exception as exc:
        return {"branch": "unknown", "last_commit": str(exc)[:80], "dirty_files": -1}


def _get_agent_activity() -> dict:
    """Return running Claude processes and recent milestone commits."""
    # Running claude processes
    running = []
    try:
        ps = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        for line in ps.stdout.splitlines():
            # Match actual claude CLI processes, not references in other commands
            if "bug_web_ui" in line or "grep" in line or "ps aux" in line:
                continue
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue
            cmd = parts[10]
            # Match actual claude binary processes
            if any(tok in cmd for tok in ["/claude ", "/claude\t", "claude --", "claude -p"]) or (parts[10].strip() == "claude"):
                running.append({
                    "pid": parts[1],
                    "cpu": parts[2],
                    "mem": parts[3],
                    "cmd": cmd[:200],
                })
    except Exception:
        pass

    # Recent milestone commits (last 20)
    milestones = []
    try:
        log = subprocess.run(
            ["git", "log", "--oneline", "-20", "--grep=milestone\\|feat\\|fix"],
            capture_output=True, text=True, timeout=5, cwd=str(REPO_ROOT),
        )
        for line in log.stdout.strip().splitlines():
            if line.strip():
                sha, _, msg = line.partition(" ")
                milestones.append({"sha": sha, "message": msg})
    except Exception:
        pass

    # Active deploy jobs from the bug UI itself
    deploy_jobs = []
    with _JOBS_LOCK:
        for fid, job in JOBS.items():
            deploy_jobs.append({
                "id": fid,
                "title": job.get("title", fid),
                "status": job.get("status", "unknown"),
            })

    # Enrich running agents with session activity from JSONL logs
    sessions_dir = Path.home() / ".claude" / "sessions"
    projects_dir = Path.home() / ".claude" / "projects"
    running_pids = {a["pid"] for a in running}

    # Also discover Claude sessions from the sessions dir that ps might have missed
    try:
        for sf in sessions_dir.glob("*.json"):
            if sf.stem.isdigit():
                pid = sf.stem
                if pid not in running_pids:
                    # Check if process is still alive
                    try:
                        os.kill(int(pid), 0)
                    except (ProcessLookupError, PermissionError):
                        continue
                    # It's alive — add it
                    try:
                        p = psutil.Process(int(pid))
                        running.append({
                            "pid": pid,
                            "cpu": str(round(p.cpu_percent(interval=0), 1)),
                            "mem": str(round(p.memory_percent(), 1)),
                            "cmd": " ".join(p.cmdline())[:200],
                        })
                        running_pids.add(pid)
                    except Exception:
                        pass
    except Exception:
        pass

    for agent in running:
        agent["session"] = _get_session_activity(int(agent["pid"]), sessions_dir, projects_dir)

    return {"running_agents": running, "milestones": milestones, "deploy_jobs": deploy_jobs}


def _get_session_activity(pid: int, sessions_dir: Path, projects_dir: Path) -> dict | None:
    """Read the JSONL conversation log for a Claude process and return recent activity."""
    # Step 1: Find session ID from sessions/<pid>.json
    pid_file = sessions_dir / f"{pid}.json"
    if not pid_file.exists():
        return None
    try:
        meta = json.loads(pid_file.read_text())
        session_id = meta.get("sessionId", "")
        cwd = meta.get("cwd", "")
        started_at = meta.get("startedAt", 0)
    except Exception:
        return None

    if not session_id:
        return None

    # Step 2: Find the JSONL log file (search all project dirs)
    jsonl_path = None
    try:
        for pdir in projects_dir.iterdir():
            candidate = pdir / f"{session_id}.jsonl"
            if candidate.exists():
                jsonl_path = candidate
                break
    except Exception:
        pass

    if not jsonl_path:
        return {"session_id": session_id, "cwd": cwd, "started_at": started_at, "activity": []}

    # Step 3: Read last ~200 lines and extract activity
    activity = []
    try:
        # Read last chunk of the file efficiently
        with open(jsonl_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            # Read last 256KB max
            read_size = min(size, 256 * 1024)
            f.seek(size - read_size)
            tail = f.read().decode("utf-8", errors="replace")

        lines = tail.strip().split("\n")
        # Parse last 150 entries
        entries = []
        for line in lines[-150:]:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

        for e in entries:
            t = e.get("type", "")
            ts = e.get("timestamp", "")
            msg = e.get("message", {})

            if t == "user":
                content = msg if isinstance(msg, str) else ""
                if isinstance(msg, dict):
                    raw = msg.get("content", "")
                    if isinstance(raw, list):
                        texts = [c.get("text", "") for c in raw if isinstance(c, dict) and c.get("type") == "text"]
                        content = " ".join(texts)
                    elif isinstance(raw, str):
                        content = raw
                if content.strip():
                    activity.append({"ts": ts[:19], "type": "user", "text": content.strip()[:200]})

            elif t == "assistant":
                content = msg.get("content", []) if isinstance(msg, dict) else []
                tools = []
                text_parts = []
                for c in (content if isinstance(content, list) else []):
                    if not isinstance(c, dict):
                        continue
                    ct = c.get("type", "")
                    if ct == "tool_use":
                        tools.append(c.get("name", ""))
                    elif ct == "text" and c.get("text", "").strip():
                        text_parts.append(c["text"].strip()[:150])
                if tools or text_parts:
                    activity.append({
                        "ts": ts[:19], "type": "assistant",
                        "tools": tools, "text": " ".join(text_parts)[:200],
                    })

        # Only keep last 20 meaningful entries
        activity = activity[-20:]
    except Exception:
        pass

    return {"session_id": session_id, "cwd": cwd, "started_at": started_at, "activity": activity}


def _load_json_safe(path) -> dict | None:
    """Return parsed JSON dict from path, or None on any error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _load_registry() -> dict:
    return _load_json_safe(REGISTRY_DB) or {}


def _save_registry(reg: dict) -> None:
    """Atomic write to REGISTRY_DB using a temp file."""
    tmp = REGISTRY_DB.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    tmp.replace(REGISTRY_DB)


def _get_latest_commit_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=str(REPO_ROOT),
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _enroll_open_issues(issues: list) -> None:
    """Persist newly-seen issues into REGISTRY_DB; update last_seen for known ones."""
    if not issues:
        return
    now = datetime.now(timezone.utc).isoformat()
    with _REGISTRY_LOCK:
        reg = _load_registry()
        changed = False
        for item in issues:
            iid = item.get("id")
            if not iid:
                continue
            if iid not in reg:
                issue0 = item.get("issues", [{}])[0]
                reg[iid] = {
                    "id": iid,
                    "agent": item.get("agent", ""),
                    "issue_type": issue0.get("type", ""),
                    "location": issue0.get("location", ""),
                    "detail": issue0.get("detail", ""),
                    "severity": item.get("severity", ""),
                    "first_seen": item.get("timestamp", now),
                    "last_seen": now,
                    "status": "open",
                    "fix": None,
                }
                changed = True
            else:
                reg[iid]["last_seen"] = now
                changed = True
        if changed:
            _save_registry(reg)


def _mark_fixed(issue_id: str, commit_sha: str, source: str, note: str) -> None:
    """Mark a registry entry as fixed. Silent no-op if id not in registry."""
    now = datetime.now(timezone.utc).isoformat()
    with _REGISTRY_LOCK:
        reg = _load_registry()
        if issue_id not in reg:
            return
        reg[issue_id]["status"] = "fixed"
        reg[issue_id]["fix"] = {
            "timestamp": now,
            "commit_sha": commit_sha,
            "source": source,
            "note": note,
        }
        _save_registry(reg)


def _get_system_resources() -> dict:
    """Return CPU, RAM, GPU, disk, and top processes."""
    cpu_pct = psutil.cpu_percent(interval=0.3)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    load1, load5, load15 = os.getloadavg()

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    disks = []
    for mnt in ["/", "/home"]:
        try:
            d = psutil.disk_usage(mnt)
            disks.append({"mount": mnt, "total_gb": round(d.total / 1e9, 1),
                          "used_gb": round(d.used / 1e9, 1), "pct": d.percent})
        except Exception:
            pass

    gpu = None
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw,power.limit",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            parts = [p.strip() for p in r.stdout.strip().split(",")]
            if len(parts) >= 5:
                gpu = {
                    "name": parts[0],
                    "vram_used_mb": int(parts[1]),
                    "vram_total_mb": int(parts[2]),
                    "vram_pct": round(int(parts[1]) / max(int(parts[2]), 1) * 100, 1),
                    "util_pct": int(parts[3]),
                    "temp_c": int(parts[4]),
                    "power_w": float(parts[5]) if len(parts) > 5 else None,
                    "power_limit_w": float(parts[6]) if len(parts) > 6 else None,
                }
    except Exception:
        pass

    top_procs = []
    for p in sorted(psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent", "memory_info", "cmdline"]),
                    key=lambda x: x.info.get("memory_percent") or 0, reverse=True)[:15]:
        info = p.info
        cmdline = " ".join(info.get("cmdline") or [])[:120] or info.get("name", "")
        mem_mb = round((info.get("memory_info").rss if info.get("memory_info") else 0) / 1e6, 1)
        top_procs.append({
            "pid": info["pid"],
            "name": info.get("name", ""),
            "cmd": cmdline,
            "mem_pct": round(info.get("memory_percent") or 0, 1),
            "mem_mb": mem_mb,
            "cpu_pct": round(info.get("cpu_percent") or 0, 1),
        })

    return {
        "cpu": {"pct": cpu_pct, "cores": cpu_count,
                "freq_mhz": round(cpu_freq.current) if cpu_freq else None,
                "load": [round(load1, 2), round(load5, 2), round(load15, 2)]},
        "ram": {"total_gb": round(mem.total / 1e9, 1), "used_gb": round(mem.used / 1e9, 1),
                "pct": mem.percent, "available_gb": round(mem.available / 1e9, 1)},
        "swap": {"total_gb": round(swap.total / 1e9, 1), "used_gb": round(swap.used / 1e9, 1),
                 "pct": swap.percent},
        "gpu": gpu,
        "disks": disks,
        "top_procs": top_procs,
    }


# ── Debate/fix knowledge base (pre-loaded for confirmed bugs) ─────────────────
KNOWN_FIXES = {
    "uuid-serialization-crash": {
        "title": "UUID Serialization Crash in pipeline_service.py",
        "file": "financial-engine_v2/backend/app/services/pipeline_service.py",
        "severity": "critical",
        "type": "BUGS",
        "explanation": (
            "The errors list built inside run_pipeline_sync() stores raw Python UUID objects "
            "as the 'document_id' field (lines 89, 98, 104). Celery is configured with "
            "task_serializer='json' (celery_app.py:53) and worker_tasks.py returns the "
            "PipelineResult directly from the task. When Celery serialises the result to JSON "
            "for storage in the Redis result backend, json.dumps() raises:\n\n"
            "  TypeError: Object of type UUID is not JSON serializable\n\n"
            "This crash only manifests in TASK_MODE=celery (production). The sync path "
            "(local dev) is unaffected. resume_pending_downloads.py correctly uses "
            "str(row.document_id) — this fix brings pipeline_service.py in line."
        ),
        "agent_a": {
            "name": "Agent A — Minimal Fix",
            "approach": "Wrap each document_id reference in str() at the three error-append sites. "
                        "Smallest possible diff, zero risk of side effects.",
            "diff": textwrap.dedent("""\
                --- a/financial-engine_v2/backend/app/services/pipeline_service.py
                +++ b/financial-engine_v2/backend/app/services/pipeline_service.py
                @@ -86,7 +86,7 @@
                             except Exception as exc:
                -                errors.append({"document_id": document_id, "stage": "download", "error": str(exc)})
                +                errors.append({"document_id": str(document_id), "stage": "download", "error": str(exc)})
                                 continue
                @@ -95,7 +95,7 @@
                                 errors.append({
                -                    "document_id": document_id,
                +                    "document_id": str(document_id),
                @@ -101,7 +101,7 @@
                             except Exception as exc:
                -                errors.append({"document_id": document_id, "stage": "process_document", "error": str(exc)})
                +                errors.append({"document_id": str(document_id), "stage": "process_document", "error": str(exc)})
            """),
        },
        "agent_b": {
            "name": "Agent B — Comprehensive Fix",
            "approach": "Extract a _make_error_entry() helper that always stringifies document_id, "
                        "ensuring any future error-append site is automatically safe. "
                        "Adds ~5 lines but makes the pattern impossible to get wrong.",
            "diff": textwrap.dedent("""\
                --- a/financial-engine_v2/backend/app/services/pipeline_service.py
                +++ b/financial-engine_v2/backend/app/services/pipeline_service.py
                @@ -79,6 +79,12 @@
                +        def _err(stage: str, exc_or_msg: str, **extra) -> dict:
                +            return {"document_id": str(document_id), "stage": stage,
                +                    "error": exc_or_msg, **extra}
                +
                         for document_id in doc_ids:
                             try:
                                 pipeline_core.download_pdf_for_document(db, document_id)
                             except Exception as exc:
                -                errors.append({"document_id": document_id, "stage": "download", "error": str(exc)})
                +                errors.append(_err("download", str(exc)))
                                 continue
                             ...
                -                errors.append({"document_id": document_id, "stage": "process_document",
                -                               "error": "extraction_failed", ...})
                +                errors.append(_err("process_document", "extraction_failed",
                +                                   extraction_status=proc_result.get("extraction_status")))
                             except Exception as exc:
                -                errors.append({"document_id": document_id, "stage": "process_document", "error": str(exc)})
                +                errors.append(_err("process_document", str(exc)))
            """),
        },
        "verdict": "Agent A wins. The helper in Agent B adds conceptual overhead for a 3-site fix. "
                   "str() at point of use is idiomatic Python and matches the pattern already used "
                   "in resume_pending_downloads.py. No abstraction needed for 3 identical one-liners.",
        "winning_agent": "a",
        "status": "open",
    },
    "extraction-failed-count-undercount": {
        "title": "extraction_failed_count Not Incremented on Exception Path",
        "file": "financial-engine_v2/backend/app/services/pipeline_service.py",
        "severity": "critical",
        "type": "BUGS",
        "explanation": (
            "In run_pipeline_sync(), the inner try/except for process_document() at line 103 "
            "appends to errors[] when an exception is raised but does NOT increment "
            "extraction_failed_count. Because processed was already incremented at line 91 "
            "(after a successful download), the formula:\n\n"
            "  processed_ok_count = processed - extraction_failed_count\n\n"
            "overcounts successful documents. Any document where process_document() throws "
            "(network timeout, LLM error, DB write failure) is silently counted as 'ok' "
            "instead of failed. This causes the quality gate in update_ticker_financials.py "
            "to also undercount extraction failures."
        ),
        "agent_a": {
            "name": "Agent A — Minimal Fix",
            "approach": "Add extraction_failed_count += 1 inside the except block. One line.",
            "diff": textwrap.dedent("""\
                --- a/financial-engine_v2/backend/app/services/pipeline_service.py
                +++ b/financial-engine_v2/backend/app/services/pipeline_service.py
                @@ -102,6 +102,7 @@
                             except Exception as exc:
                +                extraction_failed_count += 1
                                 errors.append({"document_id": str(document_id),
                                                "stage": "process_document", "error": str(exc)})
            """),
        },
        "agent_b": {
            "name": "Agent B — Comprehensive Fix",
            "approach": "Unify both failure paths (status='failed' and exception) into one counter "
                        "increment site by restructuring the if/except into a helper that always "
                        "returns (failed: bool, error_dict). Clearer invariant but larger diff.",
            "diff": textwrap.dedent("""\
                --- a/financial-engine_v2/backend/app/services/pipeline_service.py
                +++ b/financial-engine_v2/backend/app/services/pipeline_service.py
                @@ -92,18 +92,20 @@
                             if bool(spec.process_documents):
                -                try:
                -                    proc_result = pipeline_core.process_document(document_id) or {}
                -                    if (proc_result.get("extraction_status") or "").strip().lower() == "failed":
                -                        extraction_failed_count += 1
                -                        errors.append({...})
                -                except Exception as exc:
                -                    errors.append({...})
                +                failed, err = _run_process(pipeline_core, document_id)
                +                if failed:
                +                    extraction_failed_count += 1
                +                    errors.append(err)
                (where _run_process() wraps both paths and always returns a bool)
            """),
        },
        "verdict": "Agent A wins decisively. One line insertion is the correct fix. "
                   "Agent B's refactor changes control flow unnecessarily and introduces "
                   "a new helper function for a single-site fix. CLAUDE.md explicitly "
                   "prohibits unrelated refactors bundled with fixes.",
        "winning_agent": "a",
        "status": "open",
    },
    "ingestion-metrics-always-empty": {
        "title": "ingestion_metrics Always {} — 4 PipelineResult Fields Always 0",
        "file": "financial-engine_v2/backend/app/services/pipeline_service.py",
        "severity": "critical",
        "type": "REGRESSION",
        "explanation": (
            "The refactor in dc0f4a6b replaced pipeline_core._download_and_process_document_ids() "
            "which returned a populated ingestion_metrics dict, with a manual loop that "
            "initialises ingestion_metrics = {} and never populates it.\n\n"
            "PipelineResult fields now always report 0:\n"
            "  chunks_created, chunks_skipped, invalid_payloads, written_points\n\n"
            "These are read by the API, by Celery result inspection, and by monitoring scripts. "
            "Downstream dashboards and alerts that rely on these metrics receive silent zeros."
        ),
        "agent_a": {
            "name": "Agent A — Restore from pipeline_core",
            "approach": "After the loop, call pipeline_core.get_ingestion_metrics(doc_ids) "
                        "or equivalent to retrieve the real metrics. Requires checking what "
                        "pipeline_core exposes publicly.",
            "diff": "Requires reading pipeline_core.py to determine the correct public API. "
                    "Click 'Deploy Fix Agent' to have an agent investigate and propose the exact patch.",
        },
        "agent_b": {
            "name": "Agent B — Accumulate in loop",
            "approach": "Have each process_document() call return ingestion metrics and accumulate "
                        "them in the loop. Requires process_document() to return chunk counts.",
            "diff": "Requires reading process_document() return contract. "
                    "Click 'Deploy Fix Agent' to have an agent investigate and propose the exact patch.",
        },
        "verdict": "Needs investigation — the correct fix depends on what pipeline_core "
                   "exposes publicly after the refactor. Deploy a fix agent to determine the approach.",
        "winning_agent": None,
        "status": "open",
    },
    "github-action-unpinned": {
        "title": "claude-code-action@beta Pins to Mutable Tag",
        "file": ".github/workflows/claude.yml",
        "severity": "warning",
        "type": "SECURITY",
        "explanation": (
            "The workflow uses:\n  uses: anthropics/claude-code-action@beta\n\n"
            "The 'beta' tag is mutable — the action author can push new code to it at any time. "
            "If this happens maliciously or accidentally, the new code runs with:\n"
            "  - ANTHROPIC_API_KEY (from secrets)\n"
            "  - contents: write permission on the repository\n\n"
            "GitHub's own security hardening guide recommends pinning to a full commit SHA "
            "for any action that has elevated permissions. This is a supply-chain risk."
        ),
        "agent_a": {
            "name": "Agent A — Pin to SHA",
            "approach": "Resolve the current SHA of anthropics/claude-code-action@beta and pin to it. "
                        "Add a comment with the tag name for human readability.",
            "diff": textwrap.dedent("""\
                --- a/.github/workflows/claude.yml
                +++ b/.github/workflows/claude.yml
                @@ -23,7 +23,7 @@
                -      - uses: anthropics/claude-code-action@beta
                +      - uses: anthropics/claude-code-action@<SHA>  # beta
                @@ -35,7 +35,7 @@
                -      - uses: anthropics/claude-code-action@beta
                +      - uses: anthropics/claude-code-action@<SHA>  # beta
                (SHA to be resolved at deploy time via: gh api repos/anthropics/claude-code-action/git/ref/heads/beta)
            """),
        },
        "agent_b": {
            "name": "Agent B — Use Dependabot",
            "approach": "Add a .github/dependabot.yml to auto-update pinned action SHAs on a schedule. "
                        "More maintenance-friendly long-term.",
            "diff": textwrap.dedent("""\
                +++ b/.github/dependabot.yml (new file)
                +version: 2
                +updates:
                +  - package-ecosystem: github-actions
                +    directory: /
                +    schedule:
                +      interval: weekly
            """),
        },
        "verdict": "Both. Pin the SHA immediately (Agent A) and add Dependabot (Agent B) "
                   "to keep it updated automatically. The two fixes are complementary.",
        "winning_agent": "both",
        "status": "open",
    },
}

# ── Log parser ────────────────────────────────────────────────────────────────
def parse_alerts():
    if not LOG_FILE.exists():
        return []
    alerts = []
    current = None
    with open(LOG_FILE) as f:
        for line in f:
            line = line.rstrip()
            m = re.match(r'\[(.+?)\] \[(\w+)\] (severity=(\w+)|ok)\s+\((.+?)\)', line)
            if m:
                if current:
                    alerts.append(current)
                ts, agent, sev_full, severity, sha = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                current = {
                    "timestamp": ts,
                    "agent": agent,
                    "severity": severity or "ok",
                    "sha": sha,
                    "issues": [],
                    "raw": line,
                }
            elif line.startswith("  ⚠") and current:
                issue_m = re.match(r'\s+⚠\s+(.+?) @ (.+?): (.+)', line)
                if issue_m:
                    issue_dict = {
                        "type": issue_m.group(1),
                        "location": issue_m.group(2),
                        "detail": issue_m.group(3),
                    }
                    current["issues"].append(issue_dict)
                    if len(current["issues"]) == 1:  # stable id, set once on first issue
                        current["id"] = hashlib.sha1(
                            f"{current['agent']}:{issue_dict['type']}:{issue_dict['location']}:{issue_dict['detail']}".encode()
                        ).hexdigest()
    if current:
        alerts.append(current)
    return alerts


def get_open_issues():
    """Return only alerts with actual issues (non-ok severity)."""
    seen = set()
    open_issues = []
    for alert in reversed(parse_alerts()):
        if alert["issues"]:
            for issue in alert["issues"]:
                key = f"{alert['agent']}:{issue['type']}:{issue['location']}"
                if key not in seen:
                    seen.add(key)
                    open_issues.append({**alert, "issues": [issue]})
    return open_issues


def match_known_fix(alert):
    for fix_id, fix in KNOWN_FIXES.items():
        if fix["type"] == alert["agent"] and fix["severity"] == alert["severity"]:
            if alert["issues"]:
                issue = alert["issues"][0]
                if (issue["location"].split(":")[0].split("/")[-1] in fix["file"] or
                    fix["file"].split("/")[-1] in issue["location"]):
                    return fix_id, fix
    return None, None

# ── HTML template ─────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bug Monitor Dashboard</title>
<style>
:root {
  --bg: #0d1117; --surface: #161b22; --border: #30363d;
  --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
  --critical: #f85149; --warning: #e3b341; --ok: #3fb950;
  --code-bg: #1c2128;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font: 14px/1.6 'Segoe UI', system-ui, sans-serif; }
header { padding: 20px 32px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 16px; }
header h1 { font-size: 18px; font-weight: 600; }
.badge { padding: 2px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge.critical { background: rgba(248,81,73,.15); color: var(--critical); border: 1px solid rgba(248,81,73,.4); }
.badge.warning { background: rgba(227,179,65,.15); color: var(--warning); border: 1px solid rgba(227,179,65,.4); }
.badge.ok { background: rgba(63,185,80,.15); color: var(--ok); border: 1px solid rgba(63,185,80,.4); }
.badge.info { background: rgba(88,166,255,.15); color: var(--accent); border: 1px solid rgba(88,166,255,.4); }
.badge.fixed { background: rgba(63,185,80,.2); color: #3fb950; border: 1px solid rgba(63,185,80,.5); font-weight: 700; }
.bug-card.resolved { opacity: 0.7; }
.bug-card.resolved .bug-header { border-left: 3px solid #3fb950; }
.fix-meta { padding: 8px 16px; font-size: 12px; color: var(--muted); background: rgba(63,185,80,.05); border-bottom: 1px solid var(--border); }
.section-divider { padding: 16px 0 8px; }
.toggle-label { color: var(--muted); font-size: 13px; cursor: pointer; display: flex; align-items: center; gap: 6px; }
main { max-width: 1200px; margin: 0 auto; padding: 32px; }
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }
.summary-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; text-align: center; }
.summary-card .count { font-size: 36px; font-weight: 700; line-height: 1; margin-bottom: 4px; }
.summary-card .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .5px; }
.count.critical { color: var(--critical); }
.count.warning { color: var(--warning); }
.count.ok { color: var(--ok); }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.bug-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; overflow: hidden; }
.bug-header { padding: 16px 20px; display: flex; align-items: center; gap: 12px; cursor: pointer; user-select: none; }
.bug-header:hover { background: rgba(255,255,255,.03); }
.bug-title { flex: 1; font-weight: 500; }
.bug-meta { color: var(--muted); font-size: 12px; font-family: monospace; }
.chevron { transition: transform .2s; }
.bug-card.open .chevron { transform: rotate(90deg); }
.bug-body { display: none; border-top: 1px solid var(--border); }
.bug-card.open .bug-body { display: block; }
.tab-bar { display: flex; border-bottom: 1px solid var(--border); padding: 0 20px; }
.tab { padding: 10px 16px; cursor: pointer; font-size: 13px; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-content { display: none; padding: 20px; }
.tab-content.active { display: block; }
.explanation { line-height: 1.7; white-space: pre-wrap; font-size: 13px; color: var(--text); }
.agent-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
.agent-box { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 16px; }
.agent-box.winner { border-color: var(--ok); }
.agent-name { font-weight: 600; font-size: 13px; margin-bottom: 8px; }
.agent-approach { color: var(--muted); font-size: 12px; margin-bottom: 12px; }
.diff-block { background: #0d1117; border-radius: 4px; padding: 12px; font-family: monospace; font-size: 11px; overflow-x: auto; white-space: pre; line-height: 1.5; }
.diff-block .add { color: #3fb950; }
.diff-block .del { color: #f85149; }
.diff-block .hunk { color: #79c0ff; }
.verdict-box { margin-top: 16px; background: rgba(88,166,255,.08); border: 1px solid rgba(88,166,255,.3); border-radius: 6px; padding: 14px; font-size: 13px; }
.verdict-box strong { color: var(--accent); }
.deploy-btn { display: inline-flex; align-items: center; gap: 8px; margin-top: 20px; padding: 10px 20px; background: var(--ok); color: #000; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity .15s; }
.deploy-btn:hover { opacity: .85; }
.deploy-btn:disabled { opacity: .5; cursor: not-allowed; }
.deploy-btn.investigating { background: var(--warning); }
.deploy-output { margin-top: 12px; background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; font-family: monospace; font-size: 11px; white-space: pre-wrap; display: none; max-height: 300px; overflow-y: auto; }
.location-chip { font-family: monospace; font-size: 11px; background: var(--code-bg); padding: 2px 8px; border-radius: 4px; color: var(--muted); }
.ts { font-size: 11px; color: var(--muted); }
.no-issues { text-align: center; padding: 60px; color: var(--muted); }
.refresh-btn { margin-left: auto; padding: 6px 14px; background: transparent; border: 1px solid var(--border); color: var(--muted); border-radius: 6px; cursor: pointer; font-size: 12px; }
.refresh-btn:hover { border-color: var(--accent); color: var(--accent); }
.task-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px; overflow: hidden; }
.task-header { padding: 10px 16px; display: flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; }
.task-header:hover { background: rgba(255,255,255,.03); }
.task-title { flex: 1; font-size: 13px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-body { border-top: 1px solid var(--border); padding: 12px 16px; }
.task-output { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 10px; font-family: monospace; font-size: 11px; white-space: pre-wrap; max-height: 260px; overflow-y: auto; margin-bottom: 10px; }
.followup-row { display: flex; gap: 8px; }
.followup-input { flex: 1; background: var(--code-bg); border: 1px solid var(--border); border-radius: 4px; padding: 6px 10px; color: var(--text); font-size: 12px; }
.followup-input:focus { outline: none; border-color: var(--accent); }
.followup-btn { padding: 6px 14px; background: var(--accent); color: #000; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600; }
.followup-btn:disabled { opacity: .5; cursor: not-allowed; }
.cancel-btn { padding: 3px 10px; background: transparent; border: 1px solid rgba(248,81,73,.4); color: var(--critical); border-radius: 4px; cursor: pointer; font-size: 11px; }
.cancel-btn:hover { background: rgba(248,81,73,.1); }
.badge.running { background: rgba(88,166,255,.15); color: var(--accent); border: 1px solid rgba(88,166,255,.4); animation: pulse 1.5s ease-in-out infinite; }
.badge.cancelled { background: rgba(139,148,158,.15); color: var(--muted); border: 1px solid rgba(139,148,158,.4); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }

/* ── Nav tabs ──────────────────────────────────────────── */
.nav-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); padding: 0 32px; background: var(--surface); }
.nav-tab { padding: 12px 24px; cursor: pointer; font-size: 14px; font-weight: 500; color: var(--muted);
  border-bottom: 2px solid transparent; transition: all .15s; user-select: none; }
.nav-tab:hover { color: var(--text); background: rgba(255,255,255,.02); }
.nav-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.page { display: none; }
.page.active { display: block; }

/* ── System status ─────────────────────────────────────── */
.svc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-bottom: 32px; }
.svc-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; position: relative; overflow: hidden; }
.svc-card.up { border-left: 3px solid var(--ok); }
.svc-card.down { border-left: 3px solid var(--critical); }
.svc-icon { font-size: 24px; margin-bottom: 8px; }
.svc-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.svc-status { font-size: 12px; display: flex; align-items: center; gap: 6px; }
.svc-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.svc-dot.up { background: var(--ok); box-shadow: 0 0 6px var(--ok); }
.svc-dot.down { background: var(--critical); box-shadow: 0 0 6px var(--critical); }
.svc-latency { color: var(--muted); font-size: 11px; margin-top: 4px; }
.svc-detail { color: var(--muted); font-size: 11px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.git-bar { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px 20px;
  display: flex; gap: 24px; align-items: center; margin-bottom: 32px; flex-wrap: wrap; }
.git-item { font-size: 13px; }
.git-label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .5px; display: block; }

.agent-section { margin-bottom: 32px; }
.agent-proc { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px 16px;
  margin-bottom: 8px; display: flex; align-items: center; gap: 16px; font-size: 13px; cursor: pointer; transition: border-color .2s; }
.agent-proc:hover { border-color: var(--accent); }
.agent-proc.expanded { flex-wrap: wrap; }
.agent-proc.expanded .agent-cmd { white-space: pre-wrap; word-break: break-all; overflow: visible; flex-basis: 100%; margin-top: 8px; }
.agent-proc.expanded .agent-activity { display: block; flex-basis: 100%; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); }
.agent-pid { font-family: monospace; color: var(--accent); min-width: 60px; }
.agent-cmd { flex: 1; font-family: monospace; font-size: 11px; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-stat { font-size: 11px; color: var(--muted); min-width: 80px; text-align: right; }
.agent-activity { display: none; font-size: 12px; color: var(--muted); }

.milestone-list { max-height: 400px; overflow-y: auto; }
.milestone-item { display: flex; gap: 12px; align-items: baseline; padding: 6px 0; border-bottom: 1px solid rgba(48,54,61,.5); font-size: 13px; }
.milestone-sha { font-family: monospace; color: var(--accent); font-size: 12px; min-width: 70px; }
.milestone-msg { color: var(--text); }

.no-data { text-align: center; padding: 40px; color: var(--muted); font-size: 13px; }

/* ── Resource gauges ───────────────────────────── */
.gauge-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; margin-bottom: 32px; }
.gauge-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.gauge-label { font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: var(--muted); margin-bottom: 8px; display: flex; justify-content: space-between; }
.gauge-value { font-size: 28px; font-weight: 700; line-height: 1; margin-bottom: 8px; }
.gauge-bar { height: 6px; background: var(--code-bg); border-radius: 3px; overflow: hidden; margin-bottom: 6px; }
.gauge-fill { height: 100%; border-radius: 3px; transition: width .4s; }
.gauge-fill.ok { background: var(--ok); }
.gauge-fill.warn { background: var(--warning); }
.gauge-fill.crit { background: var(--critical); }
.gauge-sub { font-size: 11px; color: var(--muted); }

.proc-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 32px; }
.proc-table th { text-align: left; color: var(--muted); font-weight: 500; padding: 8px 12px; border-bottom: 1px solid var(--border);
  text-transform: uppercase; letter-spacing: .5px; font-size: 11px; cursor: pointer; user-select: none; }
.proc-table th:hover { color: var(--accent); }
.proc-table td { padding: 6px 12px; border-bottom: 1px solid rgba(48,54,61,.3); }
.proc-table tr:hover td { background: rgba(255,255,255,.02); }
.proc-cmd { font-family: monospace; font-size: 11px; color: var(--muted); max-width: 600px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer; }
.proc-cmd.expanded { white-space: pre-wrap; word-break: break-all; overflow: visible; max-width: none; }
.proc-bar { display: inline-block; height: 10px; border-radius: 2px; min-width: 2px; vertical-align: middle; margin-right: 6px; }

/* ── Session activity ──────────────────────────── */
.session-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; overflow: hidden; }
.session-header { padding: 14px 18px; display: flex; align-items: center; gap: 12px; cursor: pointer; user-select: none; }
.session-header:hover { background: rgba(255,255,255,.03); }
.session-meta { display: flex; gap: 16px; flex: 1; align-items: center; flex-wrap: wrap; }
.session-pid { font-family: monospace; color: var(--accent); font-weight: 600; }
.session-cwd { font-size: 12px; color: var(--muted); font-family: monospace; }
.session-uptime { font-size: 11px; color: var(--muted); }
.session-body { display: none; border-top: 1px solid var(--border); max-height: 400px; overflow-y: auto; }
.session-card.open .session-body { display: block; }
.session-card.open .sess-chevron { transform: rotate(90deg); }
.sess-chevron { transition: transform .2s; color: var(--muted); }
.activity-feed { padding: 0; margin: 0; list-style: none; }
.activity-item { padding: 6px 18px; border-bottom: 1px solid rgba(48,54,61,.3); display: flex; gap: 10px; font-size: 12px; }
.activity-item:last-child { border-bottom: none; }
.activity-ts { color: var(--muted); font-family: monospace; font-size: 11px; min-width: 68px; flex-shrink: 0; }
.activity-user { color: var(--warning); font-weight: 500; }
.activity-assistant { color: var(--text); }
.activity-tool { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-family: monospace;
  background: rgba(88,166,255,.1); color: var(--accent); border: 1px solid rgba(88,166,255,.2); margin-right: 4px; }
.activity-text { color: var(--muted); margin-left: 4px; }
.session-summary { font-size: 12px; color: var(--muted); max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Extraction workbench ──────────────────────── */
.ext-config { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 24px; }
.ext-row { display: flex; gap: 16px; align-items: flex-end; margin-bottom: 12px; flex-wrap: wrap; }
.ext-label { font-size: 12px; color: var(--muted); display: flex; flex-direction: column; gap: 4px; }
.ext-label select, .ext-input { background: var(--code-bg); border: 1px solid var(--border); border-radius: 4px;
  padding: 6px 10px; color: var(--text); font-size: 13px; min-width: 160px; }
.ext-label select:focus, .ext-input:focus { outline: none; border-color: var(--accent); }
.ext-check { font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 6px; cursor: pointer; }
.ext-check input { accent-color: var(--accent); }
.ext-split { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.ext-panel { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.ext-panel-title { padding: 12px 16px; font-size: 13px; font-weight: 600; border-bottom: 1px solid var(--border); }
.ext-pdf-frame { width: 100%; height: 600px; border: none; background: #1c1c1c; }
.ext-period-bar { padding: 10px 16px; display: flex; gap: 20px; font-size: 12px; color: var(--muted);
  border-bottom: 1px solid var(--border); flex-wrap: wrap; }
.ext-period-bar .period-label { color: var(--text); font-weight: 600; margin-right: 4px; }
.ext-period-bar .period-mismatch { color: var(--warning); font-weight: 600; }
.ext-accuracy { padding: 16px; font-size: 24px; font-weight: 700; text-align: center; }
.prov-link { cursor: pointer; color: var(--accent); font-size: 11px; font-family: monospace;
  text-decoration: underline dotted; white-space: nowrap; }
.prov-link:hover { color: var(--text); }
.gap-item { padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 12px; display: flex; gap: 10px; align-items: flex-start; }
.gap-item:last-child { border-bottom: none; }
.gap-type { font-family: monospace; font-size: 10px; padding: 2px 6px; border-radius: 3px; white-space: nowrap;
  background: rgba(248,81,73,.1); color: var(--critical); border: 1px solid rgba(248,81,73,.2); }
.gap-type.warn { background: rgba(210,153,34,.1); color: var(--warning); border-color: rgba(210,153,34,.2); }
.gap-field { font-weight: 600; min-width: 120px; }
.hist-row { display: flex; gap: 12px; padding: 6px 0; border-bottom: 1px solid rgba(48,54,61,.3); font-size: 12px; align-items: center; }
.hist-row:last-child { border-bottom: none; }
.hist-acc { font-weight: 700; min-width: 40px; }
.hist-bar { height: 8px; border-radius: 4px; flex: 1; max-width: 100px; background: var(--code-bg); overflow: hidden; }
.hist-bar-fill { height: 100%; border-radius: 4px; }
.retry-btn { background: none; border: 1px solid var(--border); border-radius: 4px; color: var(--accent);
  font-size: 10px; padding: 2px 6px; cursor: pointer; font-family: monospace; }
.retry-btn:hover { background: rgba(88,166,255,.1); }
.raw-table-block { margin-bottom: 16px; }
.raw-table-block summary { cursor: pointer; color: var(--accent); font-size: 12px; font-weight: 600; }
.raw-table-md { background: var(--code-bg); border: 1px solid var(--border); border-radius: 4px; padding: 10px;
  font-family: monospace; font-size: 10px; white-space: pre-wrap; max-height: 300px; overflow-y: auto; color: var(--muted); margin-top: 6px; }

/* Chat panel */
.ext-chat-container { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.ext-chat-messages { max-height: 400px; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.ext-chat-msg { padding: 10px 14px; border-radius: 8px; font-size: 13px; line-height: 1.5; max-width: 85%; white-space: pre-wrap; word-break: break-word; }
.ext-chat-msg.user { background: rgba(88,166,255,.12); border: 1px solid rgba(88,166,255,.2); align-self: flex-end; color: var(--text); }
.ext-chat-msg.assistant { background: var(--code-bg); border: 1px solid var(--border); align-self: flex-start; color: var(--text); }
.ext-chat-msg.thinking { color: var(--muted); font-style: italic; }
.ext-chat-input-row { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--border); }
.ext-chat-input { flex: 1; background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 10px 14px; color: var(--text); font-size: 13px; }
.ext-chat-input:focus { outline: none; border-color: var(--accent); }
.ext-log { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px;
  font-family: monospace; font-size: 11px; max-height: 300px; overflow-y: auto; white-space: pre-wrap; color: var(--muted); }
.ext-raw { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px;
  font-family: monospace; font-size: 11px; max-height: 400px; overflow: auto; white-space: pre-wrap; color: var(--muted); }
.ext-elapsed { font-size: 12px; color: var(--muted); margin-left: 8px; }
.metric-match { color: var(--ok); }
.metric-miss { color: var(--critical); }
.metric-null { color: var(--muted); }
@media (max-width: 900px) { .ext-split { grid-template-columns: 1fr; } }

/* Floating chat button */
.chat-fab { position: fixed; bottom: 24px; right: 24px; width: 56px; height: 56px; border-radius: 50%;
  background: var(--accent); color: #fff; border: none; font-size: 24px; cursor: pointer; z-index: 1000;
  box-shadow: 0 4px 16px rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center;
  transition: transform .2s, box-shadow .2s; }
.chat-fab:hover { transform: scale(1.1); box-shadow: 0 6px 24px rgba(0,0,0,.5); }
.chat-fab.has-session { background: var(--ok); }

/* Chat drawer */
.chat-drawer { position: fixed; bottom: 90px; right: 24px; width: 380px; max-height: 480px; z-index: 999;
  background: var(--bg); border: 1px solid var(--border); border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,.5);
  display: none; flex-direction: column; overflow: hidden; }
.chat-drawer.open { display: flex; }
.chat-drawer-header { padding: 10px 12px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; flex-wrap: nowrap; }
.chat-drawer-header select { flex: 1; min-width: 0; background: var(--code-bg); border: 1px solid var(--border); border-radius: 4px;
  color: var(--text); padding: 5px 6px; font-size: 11px; overflow: hidden; text-overflow: ellipsis; }
.chat-drawer-header .badge { font-size: 10px; flex-shrink: 0; }
.chat-drawer-messages { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 8px; min-height: 150px; }
.chat-drawer-input { display: flex; gap: 6px; padding: 8px 10px; border-top: 1px solid var(--border); align-items: center; }
.chat-drawer-input input { flex: 1; min-width: 0; background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px;
  padding: 8px 10px; color: var(--text); font-size: 13px; }
.chat-drawer-input input:focus { outline: none; border-color: var(--accent); }
.chat-drawer-input button { background: var(--accent); color: #fff; border: none; border-radius: 6px; padding: 8px 12px;
  cursor: pointer; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.chat-drawer-input button:disabled { opacity: .5; cursor: default; }
.chat-screenshot-btn { background: none; border: 1px solid var(--border); border-radius: 6px; padding: 5px 8px;
  cursor: pointer; color: var(--muted); font-size: 13px; flex-shrink: 0; line-height: 1; }
.chat-screenshot-btn:hover { border-color: var(--accent); color: var(--accent); }
</style>
<script src="https://unpkg.com/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
</head>
<body>
<header>
  <h1>🔍 Tenn Dashboard</h1>
  <span class="badge info" id="last-updated">loading…</span>
  <button class="refresh-btn" onclick="refreshAll()">↺ Refresh</button>
</header>
<div class="nav-tabs">
  <div class="nav-tab active" data-page="bugs" onclick="switchPage('bugs')">🐛 Bugs</div>
  <div class="nav-tab" data-page="system" onclick="switchPage('system')">🖥 System</div>
  <div class="nav-tab" data-page="extraction" onclick="switchPage('extraction')">🧪 Extraction</div>
</div>

<!-- ── Bugs page ── -->
<main class="page active" id="page-bugs">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
    <button class="deploy-btn" id="scan-btn" onclick="runMonitorScan()" style="font-size:13px;padding:8px 16px">
      &#x1f50d; Scan for new bugs
    </button>
    <span id="scan-status" style="font-size:12px;color:var(--muted)"></span>
  </div>
  <div class="summary" id="summary"></div>
  <div id="tasks-section" style="display:none">
    <div class="section-title">Agent Tasks</div>
    <div id="tasks-list"></div>
  </div>
  <div class="section-title">Open Issues</div>
  <div id="issues-list"></div>
</main>

<!-- ── System page ── -->
<main class="page" id="page-system">
  <div id="git-bar" class="git-bar" style="display:none"></div>

  <div class="section-title">Resources</div>
  <div class="gauge-grid" id="gauge-grid"></div>

  <div class="section-title">Services</div>
  <div class="svc-grid" id="svc-grid"></div>

  <div class="section-title">Top Processes by Memory</div>
  <table class="proc-table" id="proc-table">
    <thead><tr>
      <th data-sort="pid">PID</th>
      <th data-sort="name">Name</th>
      <th data-sort="mem_pct">MEM %</th>
      <th data-sort="mem_mb">MEM MB</th>
      <th data-sort="cpu_pct">CPU %</th>
      <th>Command</th>
    </tr></thead>
    <tbody id="proc-body"></tbody>
  </table>

  <div class="section-title">Running Claude Sessions</div>
  <div class="agent-section" id="agent-procs"></div>

  <div class="section-title">Deploy Jobs</div>
  <div class="agent-section" id="deploy-jobs"></div>

  <div class="section-title">Recent Milestones</div>
  <div class="milestone-list" id="milestones"></div>
</main>

<!-- ── Extraction page ── -->
<main class="page" id="page-extraction">
  <!-- Config panel -->
  <div class="section-title">Extraction Config</div>
  <div class="ext-config" id="ext-config">
    <div class="ext-row">
      <label class="ext-label">Source
        <select id="ext-source" onchange="onExtSourceChange()">
          <option value="fixture">Eval Fixture</option>
          <option value="custom">Custom PDF</option>
        </select>
      </label>
      <label class="ext-label" id="ext-fixture-label">Fixture
        <select id="ext-fixture"></select>
      </label>
      <label class="ext-label" id="ext-ticker-label" style="display:none">Ticker
        <select id="ext-ticker" onchange="onExtTickerChange()"><option value="">All</option></select>
      </label>
      <label class="ext-label" id="ext-pdf-label" style="display:none">PDF
        <select id="ext-pdf"></select>
      </label>
    </div>
    <div class="ext-row">
      <label class="ext-label">Model
        <input type="text" id="ext-model" value="qwen2.5-14b-instruct" class="ext-input">
      </label>
      <label class="ext-label">LLM URL
        <input type="text" id="ext-url" value="" placeholder="default (from config)" class="ext-input" style="width:220px">
      </label>
    </div>
    <div class="ext-row">
      <label class="ext-check"><input type="checkbox" id="ext-force-pymupdf"> Force PyMuPDF (skip docling)</label>
      <label class="ext-check"><input type="checkbox" id="ext-skip-narrative" checked> Skip narrative</label>
      <label class="ext-check"><input type="checkbox" id="ext-no-parallel"> Disable parallel</label>
      <label class="ext-check"><input type="checkbox" id="ext-no-filter"> Disable row filtering</label>
      <label class="ext-check"><input type="checkbox" id="ext-no-skip-redundant"> Disable redundant skip</label>
    </div>
    <div class="ext-row">
      <button class="deploy-btn" id="ext-run-btn" onclick="runExtraction()">▶ Run Extraction</button>
    </div>
  </div>

  <!-- Results -->
  <div id="ext-results" style="display:none">
    <div class="section-title">Results <span class="badge" id="ext-status-badge"></span> <span id="ext-elapsed" class="ext-elapsed"></span></div>

    <div class="ext-split">
      <!-- Metrics comparison -->
      <div class="ext-panel">
        <div class="ext-panel-title">Metrics Comparison</div>
        <div id="ext-period-bar" class="ext-period-bar"></div>
        <div id="ext-accuracy" class="ext-accuracy"></div>
        <table class="proc-table" id="ext-metrics-table">
          <thead>
            <tr id="ext-period-row" style="display:none">
              <td colspan="6" style="padding:10px 12px;background:var(--code-bg);font-size:12px" id="ext-period-cell"></td>
            </tr>
            <tr>
              <th title="Financial metric name">Metric</th>
              <th title="Value extracted by the LLM from the PDF">Extracted</th>
              <th title="Hand-verified ground truth from eval fixture">Expected</th>
              <th title="Percentage difference: |extracted - expected| / |expected|">Diff</th>
              <th title="Source table, page number, and row where the value was found">Source</th>
              <th title="Match or miss against tolerance threshold">Status</th>
            </tr>
          </thead>
          <tbody id="ext-metrics-body"></tbody>
        </table>
      </div>
      <!-- PDF viewer -->
      <div class="ext-panel">
        <div class="ext-panel-title">Document</div>
        <iframe id="ext-pdf-viewer" class="ext-pdf-frame" src="about:blank"></iframe>
      </div>
    </div>

    <!-- Gaps & diagnostics -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:24px">
      <div class="ext-panel">
        <div class="ext-panel-title">Quality Gaps <span class="badge" id="ext-gap-count"></span></div>
        <div id="ext-gaps" style="padding:12px;max-height:300px;overflow-y:auto"></div>
      </div>
      <div class="ext-panel">
        <div class="ext-panel-title">History <span style="font-size:11px;color:var(--muted)">(last runs for this fixture)</span></div>
        <div id="ext-history" style="padding:12px;max-height:300px;overflow-y:auto"></div>
      </div>
    </div>

    <!-- Raw tables viewer -->
    <details style="margin-top:16px">
      <summary style="cursor:pointer;color:var(--muted);font-size:13px">Source Tables (raw markdown from PDF)</summary>
      <div id="ext-raw-tables" style="padding:12px"></div>
    </details>

    <!-- Extraction log -->
    <div class="section-title" style="margin-top:24px">Extraction Log</div>
    <div class="ext-log" id="ext-log"></div>

    <!-- Raw payload -->
    <details style="margin-top:16px">
      <summary style="cursor:pointer;color:var(--muted);font-size:13px">Raw Payload</summary>
      <pre class="ext-raw" id="ext-raw"></pre>
    </details>

    <!-- Retry result -->
    <div id="ext-retry-panel" style="display:none;margin-top:16px">
      <div class="section-title">Retry Result <span class="badge" id="ext-retry-status"></span></div>
      <div class="ext-log" id="ext-retry-log"></div>
      <pre class="ext-raw" id="ext-retry-raw" style="margin-top:8px"></pre>
    </div>

    <!-- Chat with Claude about this extraction -->
    <div id="ext-chat-panel" style="display:none;margin-top:24px">
      <div class="section-title">Chat with Claude <span class="badge" id="ext-chat-status">ready</span></div>
      <div class="ext-chat-container">
        <div class="ext-chat-messages" id="ext-chat-messages"></div>
        <div class="ext-chat-input-row">
          <input type="text" class="ext-chat-input" id="ext-chat-input"
            placeholder="Ask about the extraction results..." autocomplete="off">
          <button class="deploy-btn" id="ext-chat-send" onclick="sendChatMessage()">Send</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Fixture overview -->
  <div class="section-title" style="margin-top:32px">Eval Fixtures</div>
  <table class="proc-table" id="ext-fixtures-table">
    <thead><tr><th>Fixture</th><th>Ticker</th><th>Period</th><th>Date</th><th>Currency</th><th>Scale</th><th>Metrics</th><th>PDF</th></tr></thead>
    <tbody id="ext-fixtures-body"></tbody>
  </table>
</main>

<script>
let allData = [];
let _pendingOps = 0;

// ── Task panel ────────────────────────────────────────────────────────────────
function ensureTaskCard(fixId, title) {
  document.getElementById('tasks-section').style.display = 'block';
  if (document.getElementById('task-' + fixId)) return;

  const header = document.createElement('div');
  header.className = 'task-header';
  header.addEventListener('click', function() {
    const b = document.getElementById('task-body-' + fixId);
    if (b) b.style.display = b.style.display === 'none' ? 'block' : 'none';
  });
  const badge = document.createElement('span');
  badge.id = 'task-status-' + fixId;
  badge.className = 'badge running';
  badge.textContent = 'running';
  const titleEl = document.createElement('span');
  titleEl.className = 'task-title';
  titleEl.title = title;
  titleEl.textContent = title;
  const cancelBtn = document.createElement('button');
  cancelBtn.id = 'task-cancel-' + fixId;
  cancelBtn.className = 'cancel-btn';
  cancelBtn.textContent = '\u2715 Cancel';
  cancelBtn.addEventListener('click', function(e) { e.stopPropagation(); cancelTask(fixId); });
  header.append(badge, titleEl, cancelBtn);

  const outEl = document.createElement('div');
  outEl.id = 'task-out-' + fixId;
  outEl.className = 'task-output';
  outEl.textContent = 'Starting\u2026';
  const inputEl = document.createElement('input');
  inputEl.id = 'followup-' + fixId;
  inputEl.className = 'followup-input';
  inputEl.placeholder = 'Ask a follow-up question\u2026';
  inputEl.addEventListener('keydown', function(e) { if (e.key === 'Enter') askFollowUp(fixId); });
  const askBtn = document.createElement('button');
  askBtn.className = 'followup-btn';
  askBtn.textContent = 'Ask \u21b5';
  askBtn.addEventListener('click', function() { askFollowUp(fixId); });
  const followupRow = document.createElement('div');
  followupRow.className = 'followup-row';
  followupRow.append(inputEl, askBtn);
  const body = document.createElement('div');
  body.id = 'task-body-' + fixId;
  body.className = 'task-body';
  body.append(outEl, followupRow);

  const card = document.createElement('div');
  card.id = 'task-' + fixId;
  card.className = 'task-card';
  card.append(header, body);
  document.getElementById('tasks-list').prepend(card);
}

function updateTaskStatus(fixId, status) {
  const badge = document.getElementById('task-status-' + fixId);
  if (badge) { badge.className = 'badge ' + status; badge.textContent = status; }
  const btn = document.getElementById('task-cancel-' + fixId);
  if (btn) btn.style.display = status === 'running' ? '' : 'none';
}

function appendTaskOutput(fixId, lines) {
  const el = document.getElementById('task-out-' + fixId);
  if (!el) return;
  el.textContent += lines + '\n';
  el.scrollTop = el.scrollHeight;
}

function setTaskOutput(fixId, text) {
  const el = document.getElementById('task-out-' + fixId);
  if (el) { el.textContent = text; el.scrollTop = el.scrollHeight; }
}

async function cancelTask(fixId) {
  const resp = await fetch('/api/job/' + encodeURIComponent(fixId) + '/cancel', {method: 'POST'});
  const data = await resp.json();
  if (data.ok) {
    updateTaskStatus(fixId, 'cancelled');
    _pendingOps = Math.max(0, _pendingOps - 1);
    appendTaskOutput(fixId, '[cancelled]');
  }
}

async function askFollowUp(fixId) {
  const inputEl = document.getElementById('followup-' + fixId);
  const question = inputEl ? inputEl.value.trim() : '';
  if (!question) return;
  const askBtn = inputEl && inputEl.nextElementSibling;
  inputEl.value = ''; inputEl.disabled = true; if (askBtn) askBtn.disabled = true;
  try {
    const resp = await fetch('/api/job/' + encodeURIComponent(fixId) + '/followup', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question}),
    });
    const data = await resp.json();
    if (data.ok && data.job_id) {
      ensureTaskCard(data.job_id, 'Q: ' + question.slice(0, 60));
      setTaskOutput(data.job_id, 'Asking\u2026');
      _pendingOps++;
      pollTask(data.job_id, {lastLen: 0});
    } else {
      appendTaskOutput(fixId, 'Follow-up error: ' + (data.message || 'unknown'));
    }
  } catch(e) {
    appendTaskOutput(fixId, 'Error: ' + e.message);
  } finally {
    inputEl.disabled = false; if (askBtn) askBtn.disabled = false;
  }
}

function pollTask(fixId, state) {
  fetch('/api/job/' + encodeURIComponent(fixId))
    .then(function(r){ return r.json(); })
    .then(function(job) {
      if (job.output && job.output.length > state.lastLen) {
        appendTaskOutput(fixId, job.output.slice(state.lastLen).join('\n'));
        state.lastLen = job.output.length;
      }
      updateTaskStatus(fixId, job.status);
      if (job.status === 'running') {
        setTimeout(function(){ pollTask(fixId, state); }, 1500);
      } else {
        _pendingOps = Math.max(0, _pendingOps - 1);
      }
    })
    .catch(function(e) {
      appendTaskOutput(fixId, 'Poll error: ' + e.message);
      updateTaskStatus(fixId, 'error');
      _pendingOps = Math.max(0, _pendingOps - 1);
    });
}

async function loadJobs() {
  try {
    const resp = await fetch('/api/jobs');
    const jobs = await resp.json();
    Object.entries(jobs).forEach(function([fixId, job]) {
      ensureTaskCard(fixId, job.title || fixId);
      if (job.output && job.output.length) setTaskOutput(fixId, job.output.join('\n'));
      updateTaskStatus(fixId, job.status);
      if (job.status === 'running') {
        _pendingOps++;
        pollTask(fixId, {lastLen: job.output ? job.output.length : 0});
      }
    });
  } catch(e) { /* no jobs yet */ }
}

function colorDiff(diff) {
  return diff.split('\n').map(l => {
    if (l.startsWith('+++') || l.startsWith('---')) return `<span class="hunk">${esc(l)}</span>`;
    if (l.startsWith('+')) return `<span class="add">${esc(l)}</span>`;
    if (l.startsWith('-')) return `<span class="del">${esc(l)}</span>`;
    if (l.startsWith('@@')) return `<span class="hunk">${esc(l)}</span>`;
    return esc(l);
  }).join('\n');
}

function esc(s) {
  return (s == null ? '' : String(s)).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderDiff(diff) {
  return `<div class="diff-block">${colorDiff(diff)}</div>`;
}

function makeBugCard(item) {
  const sev = item.severity;
  const fix_id = item.fix_id;
  const fix = item.known_fix;
  const issue = item.issues[0];
  const id = `card-${item.id}`;

  let bodyHtml = '';
  if (fix) {
    const winA = fix.winning_agent === 'a' || fix.winning_agent === 'both';
    const winB = fix.winning_agent === 'b' || fix.winning_agent === 'both';
    bodyHtml = `
      <div class="tab-bar">
        <div class="tab active" onclick="switchTab(this,'${id}-explanation')">Explanation</div>
        <div class="tab" onclick="switchTab(this,'${id}-debate')">Agent Debate</div>
        <div class="tab" onclick="switchTab(this,'${id}-fix')">Proposed Fix</div>
      </div>
      <div class="tab-content active" id="${id}-explanation">
        <div class="explanation">${esc(fix.explanation)}</div>
      </div>
      <div class="tab-content" id="${id}-debate">
        <div class="agent-row">
          <div class="agent-box ${winA?'winner':''}">
            <div class="agent-name">${esc(fix.agent_a.name)} ${winA?'✓':''}</div>
            <div class="agent-approach">${esc(fix.agent_a.approach)}</div>
            ${fix.agent_a.diff && !fix.agent_a.diff.includes('Deploy Fix') ? renderDiff(fix.agent_a.diff) : `<div class="agent-approach">${esc(fix.agent_a.diff||'')}</div>`}
          </div>
          <div class="agent-box ${winB?'winner':''}">
            <div class="agent-name">${esc(fix.agent_b.name)} ${winB?'✓':''}</div>
            <div class="agent-approach">${esc(fix.agent_b.approach)}</div>
            ${fix.agent_b.diff && !fix.agent_b.diff.includes('Deploy Fix') ? renderDiff(fix.agent_b.diff) : `<div class="agent-approach">${esc(fix.agent_b.diff||'')}</div>`}
          </div>
        </div>
        <div class="verdict-box"><strong>Verdict:</strong> ${esc(fix.verdict)}</div>
      </div>
      <div class="tab-content" id="${id}-fix">
        ${fix.winning_agent && fix.agent_a.diff && !fix.agent_a.diff.includes('Deploy Fix')
          ? renderDiff(fix.winning_agent === 'b' ? fix.agent_b.diff : fix.agent_a.diff)
          : '<div class="explanation">Deploy an agent to investigate and generate the exact patch.</div>'}
        <button class="deploy-btn ${fix.winning_agent?'':'investigating'}"
                onclick="deployFix('${fix_id}', this)"
                id="deploy-${fix_id}">
          ${fix.winning_agent ? '▶ Deploy Fix Agent' : '🔍 Investigate & Fix'}
        </button>
        <div class="deploy-output" id="output-${fix_id}"></div>
      </div>`;
  } else {
    bodyHtml = `
      <div class="tab-bar">
        <div class="tab active" onclick="switchTab(this,'${id}-explanation')">Issue</div>
      </div>
      <div class="tab-content active" id="${id}-explanation">
        <div class="explanation">${esc(issue.detail)}</div>
        <button class="deploy-btn investigating" onclick="loadDebate('${item.id}', allData.find(function(d){return d.id==='${item.id}'}))" id="debate-${item.id}">
          \uD83D\uDD0D Get AI Analysis
        </button>
      </div>`;
  }

  const regStatus = item.registry && item.registry.status;
  const statusBadge = regStatus === 'fixed'
    ? '<span class="badge fixed">FIXED</span>'
    : '';
  const fixMeta = (regStatus === 'fixed' && item.registry.fix)
    ? `<div class="fix-meta">Fixed ${esc(item.registry.fix.timestamp.split('T')[0])} · ${esc(item.registry.fix.source)} · commit ${esc((item.registry.fix.commit_sha||'').slice(0,8))}</div>`
    : '';

  return `
    <div class="bug-card ${regStatus === 'fixed' ? 'resolved' : ''}" id="${id}">
      <div class="bug-header" onclick="toggleCard('${id}')">
        <span class="badge ${sev}">${sev}</span>
        ${statusBadge}
        <span class="badge info">${esc(item.agent)}</span>
        <span class="bug-title">${fix ? esc(fix.title) : esc(issue.type.replace(/-/g,' '))}</span>
        <span class="location-chip">${esc(issue.location)}</span>
        <span class="ts">${item.timestamp ? item.timestamp.split('T')[1].split('+')[0] : ''}</span>
        <span class="chevron">›</span>
      </div>
      <div class="bug-body">${fixMeta}${bodyHtml}</div>
    </div>`;
}

function switchTab(el, targetId) {
  const bar = el.closest('.tab-bar');
  bar.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const body = bar.closest('.bug-body');
  body.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById(targetId)?.classList.add('active');
}

function toggleCard(id) {
  document.getElementById(id)?.classList.toggle('open');
}

async function deployFix(fixId, btn) {
  _pendingOps++;
  btn.disabled = true;
  btn.textContent = '\u23F3 Deploying\u2026';

  // Register in the persistent task panel so output survives page re-renders
  const cardEl = btn.closest('[id^="card-"]');
  const titleEl = cardEl && cardEl.querySelector('.bug-title');
  const title = (titleEl && titleEl.textContent.trim()) || fixId;
  ensureTaskCard(fixId, title);

  const out = document.getElementById('output-' + fixId);
  out.style.display = 'block';
  out.textContent = '\u2191 Streaming in Agent Tasks above\n';

  try {
    const resp = await fetch('/api/deploy/' + encodeURIComponent(fixId), {method: 'POST'});
    const data = await resp.json();
    if (!data.ok) {
      const msg = data.message || JSON.stringify(data, null, 2);
      out.textContent = msg;
      appendTaskOutput(fixId, msg);
      updateTaskStatus(fixId, 'error');
      btn.disabled = false;
      btn.textContent = '\u21BA Retry';
      _pendingOps--;
      return;
    }
    appendTaskOutput(fixId, 'Agent spawned\u2026');
    let lastLen = 0;
    function poll() {
      fetch('/api/job/' + encodeURIComponent(fixId))
        .then(function(r){ return r.json(); })
        .then(function(job) {
          if (job.output && job.output.length > lastLen) {
            appendTaskOutput(fixId, job.output.slice(lastLen).join('\n'));
            lastLen = job.output.length;
          }
          updateTaskStatus(fixId, job.status);
          if (job.status === 'running') {
            setTimeout(poll, 1500);
          } else if (job.status === 'done') {
            _pendingOps--;
            btn.textContent = '\u2713 Fix Applied';
            btn.style.background = 'var(--ok)';
          } else {
            _pendingOps--;
            btn.disabled = false;
            btn.textContent = '\u21BA Retry';
          }
        })
        .catch(function(e) {
          _pendingOps--;
          const errMsg = 'Poll error: ' + e.message;
          appendTaskOutput(fixId, errMsg);
          updateTaskStatus(fixId, 'error');
          btn.disabled = false;
          btn.textContent = '\u21BA Retry';
        });
    }
    setTimeout(poll, 1500);
  } catch(e) {
    _pendingOps--;
    const errMsg = 'Error: ' + e.message;
    out.textContent = errMsg;
    appendTaskOutput(fixId, errMsg);
    updateTaskStatus(fixId, 'error');
    btn.disabled = false;
    btn.textContent = '\u21BA Retry';
  }
}

async function loadDebate(issueId, itemData) {
  if (!itemData) return;
  const cardId = 'card-' + itemData.id;
  const card = document.getElementById(cardId);
  const body = card && card.querySelector('.bug-body');
  if (!body) return;
  _pendingOps++;
  const spinner = document.createElement('div');
  spinner.style.cssText = 'padding:20px;color:var(--muted)';
  spinner.textContent = '\u23F3 Generating agent debate\u2026';
  body.textContent = '';
  body.appendChild(spinner);

  try {
    const resp = await fetch('/api/debate/' + issueId, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({agent: itemData.agent, severity: itemData.severity, issues: itemData.issues}),
    });
    const debate = await resp.json();
    if (!resp.ok || debate.ok === false) {
      const err = document.createElement('div');
      err.style.cssText = 'padding:20px;color:var(--critical)';
      err.textContent = 'Debate failed: ' + (debate.message || 'unknown error');
      body.textContent = '';
      body.appendChild(err);
      return;
    }
    const item = allData.find(function(d){ return d.id === issueId; });
    if (item) {
      item.known_fix = debate;
      item.fix_id = issueId;
      const tmp = document.createElement('div');
      tmp.innerHTML = makeBugCard(item);
      card.replaceWith(tmp.firstChild);
      const updated = document.getElementById(cardId);
      if (updated) updated.classList.add('open');
    }
  } catch(e) {
    const err = document.createElement('div');
    err.style.cssText = 'padding:20px;color:var(--critical)';
    err.textContent = 'Error: ' + e.message;
    body.textContent = '';
    body.appendChild(err);
  } finally {
    _pendingOps--;
  }
}

async function loadData() {
  const resp = await fetch('/api/data');
  const data = await resp.json();
  allData = data;

  document.getElementById('last-updated').textContent =
    `Updated ${new Date().toLocaleTimeString()}`;

  // Don't replace the card list while a deploy or debate is in progress —
  // it would destroy the output div and leave the polling loop writing
  // into a detached DOM node the user can never see.
  if (_pendingOps > 0) return;

  const openIssues = data.filter(d => (d.severity === 'critical' || d.severity === 'warning') && (!d.registry || d.registry.status !== 'fixed'));
  const fixedIssues = data.filter(d => d.registry && d.registry.status === 'fixed');
  const critCount = openIssues.filter(d => d.severity === 'critical').length;
  const warnCount = openIssues.filter(d => d.severity === 'warning').length;
  document.getElementById('summary').innerHTML = `
    <div class="summary-card"><div class="count critical">${critCount}</div><div class="label">Critical</div></div>
    <div class="summary-card"><div class="count warning">${warnCount}</div><div class="label">Warnings</div></div>
    <div class="summary-card"><div class="count ok">${fixedIssues.length}</div><div class="label">Fixed</div></div>
    <div class="summary-card"><div class="count">${data.length}</div><div class="label">Total</div></div>
  `;

  const list = document.getElementById('issues-list');

  // Sort: critical first
  openIssues.sort((a,b) => {
    const order = {critical:0, warning:1};
    return (order[a.severity]??2) - (order[b.severity]??2);
  });

  let html = '';
  if (openIssues.length) {
    html += openIssues.map(makeBugCard).join('');
  } else {
    html += '<div class="no-issues">\u2713 No open issues</div>';
  }

  if (fixedIssues.length) {
    const showFixed = document.getElementById('show-fixed-toggle');
    const isExpanded = showFixed && showFixed.checked;
    html += `<div class="section-divider">
      <label class="toggle-label"><input type="checkbox" id="show-fixed-toggle"
        ${isExpanded ? 'checked' : ''}
        onchange="document.getElementById('fixed-list').style.display = this.checked ? 'block' : 'none'">
        Show ${fixedIssues.length} resolved issue${fixedIssues.length > 1 ? 's' : ''}</label>
    </div>`;
    html += `<div id="fixed-list" style="display:${isExpanded ? 'block' : 'none'}">`;
    html += fixedIssues.map(makeBugCard).join('');
    html += '</div>';
  }

  list.innerHTML = html;
}

// ── Navigation ───────────────────────────────────────────────────────────────
function switchPage(page) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.page === page));
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + page));
  if (page === 'system') loadSystem();
  if (page === 'extraction') loadExtraction();
}

// ── System status ────────────────────────────────────────────────────────────
async function loadSystem() {
  try {
    const resp = await fetch('/api/system');
    const data = await resp.json();
    renderResources(data.resources);
    renderServices(data.services);
    renderGit(data.git);
    renderAgents(data.agents);
    renderProcs(data.resources.top_procs);
  } catch (e) {
    document.getElementById('svc-grid').textContent = 'Failed to load system status';
  }
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function timeSince(epochMs) {
  const secs = Math.floor((Date.now() - epochMs) / 1000);
  if (secs < 60) return secs + 's';
  const mins = Math.floor(secs / 60);
  if (mins < 60) return mins + 'm';
  const hrs = Math.floor(mins / 60);
  const rm = mins % 60;
  return hrs + 'h ' + rm + 'm';
}

function barClass(pct) { return pct > 90 ? 'crit' : pct > 70 ? 'warn' : 'ok'; }

function makeGauge(label, value, pct, sub, icon) {
  const cls = barClass(pct);
  return '<div class="gauge-card">'
    + '<div class="gauge-label"><span>' + esc(icon + ' ' + label) + '</span><span>' + esc(sub) + '</span></div>'
    + '<div class="gauge-value" style="color:var(--' + cls + ')">' + esc(String(Math.round(pct))) + '%</div>'
    + '<div class="gauge-bar"><div class="gauge-fill ' + cls + '" style="width:' + pct + '%"></div></div>'
    + '<div class="gauge-sub">' + esc(value) + '</div></div>';
}

function renderResources(r) {
  const grid = document.getElementById('gauge-grid');
  let html = '';

  // CPU
  const cpu = r.cpu;
  html += makeGauge('CPU', cpu.cores + ' cores @ ' + (cpu.freq_mhz || '?') + ' MHz',
    cpu.pct, 'Load: ' + cpu.load.join(' / '), '\u2699\ufe0f');

  // RAM
  const ram = r.ram;
  html += makeGauge('RAM', ram.used_gb + ' / ' + ram.total_gb + ' GB',
    ram.pct, ram.available_gb + ' GB available', '\ud83d\udcbe');

  // GPU
  if (r.gpu) {
    const g = r.gpu;
    html += makeGauge('GPU Compute', g.name,
      g.util_pct, g.temp_c + '\u00b0C' + (g.power_w ? ' \u00b7 ' + Math.round(g.power_w) + '/' + Math.round(g.power_limit_w) + 'W' : ''), '\ud83c\udfae');
    html += makeGauge('VRAM', g.vram_used_mb + ' / ' + g.vram_total_mb + ' MB',
      g.vram_pct, (g.vram_total_mb - g.vram_used_mb) + ' MB free', '\ud83e\udde0');
  }

  // Swap (disk used as overflow when RAM is full — high usage = memory pressure)
  if (r.swap && r.swap.total_gb > 0) {
    var swapNote = r.swap.pct > 80 ? 'memory pressure — consider closing processes' : '';
    html += makeGauge('Swap (overflow RAM)', r.swap.used_gb + ' / ' + r.swap.total_gb + ' GB',
      r.swap.pct, swapNote, '\ud83d\udd04');
  }

  // Disks
  r.disks.forEach(function(d) {
    html += makeGauge('Disk ' + d.mount, d.used_gb + ' / ' + d.total_gb + ' GB',
      d.pct, '', '\ud83d\udcbf');
  });

  grid.innerHTML = html;
}

let _procSort = {col: 'mem_pct', asc: false};
let _procData = [];

function renderProcs(procs) {
  _procData = procs;
  _sortAndRenderProcs();
}

function _sortAndRenderProcs() {
  const sorted = [..._procData].sort(function(a, b) {
    const va = a[_procSort.col], vb = b[_procSort.col];
    if (typeof va === 'number') return _procSort.asc ? va - vb : vb - va;
    return _procSort.asc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });
  const body = document.getElementById('proc-body');
  body.textContent = '';
  sorted.forEach(function(p) {
    const tr = document.createElement('tr');
    const memBar = '<span class="proc-bar ' + barClass(p.mem_pct * 2) + '" style="width:' + Math.max(p.mem_pct * 2, 2) + 'px;background:var(--' + barClass(p.mem_pct * 2) + ')"></span>';
    const cpuBar = '<span class="proc-bar ' + barClass(p.cpu_pct) + '" style="width:' + Math.max(p.cpu_pct, 2) + 'px;background:var(--' + barClass(p.cpu_pct) + ')"></span>';
    tr.innerHTML = '<td>' + esc(String(p.pid)) + '</td>'
      + '<td>' + esc(p.name) + '</td>'
      + '<td>' + memBar + esc(String(p.mem_pct)) + '</td>'
      + '<td>' + esc(String(p.mem_mb)) + '</td>'
      + '<td>' + cpuBar + esc(String(p.cpu_pct)) + '</td>'
      + '<td class="proc-cmd" title="Click to expand">' + esc(p.cmd) + '</td>';
    tr.querySelector('.proc-cmd').addEventListener('click', function(e) {
      e.currentTarget.classList.toggle('expanded');
    });
    body.appendChild(tr);
  });
}

// Column sort for proc table
document.getElementById('proc-table').addEventListener('click', function(e) {
  const th = e.target.closest('th[data-sort]');
  if (!th) return;
  const col = th.dataset.sort;
  if (_procSort.col === col) _procSort.asc = !_procSort.asc;
  else { _procSort.col = col; _procSort.asc = false; }
  _sortAndRenderProcs();
});

function renderServices(services) {
  const grid = document.getElementById('svc-grid');
  grid.textContent = '';
  services.forEach(s => {
    const card = document.createElement('div');
    card.className = 'svc-card ' + s.status;
    const latency = s.latency_ms != null ? '<div class="svc-latency">' + esc(s.latency_ms + 'ms') + '</div>' : '';
    card.innerHTML = '<div class="svc-icon">' + esc(s.icon || '\u25cf') + '</div>'
      + '<div class="svc-name">' + esc(s.name) + '</div>'
      + '<div class="svc-status"><span class="svc-dot ' + s.status + '"></span>'
      + (s.status === 'up' ? 'Healthy' : 'Down')
      + '<span style="margin-left:auto;font-size:11px;color:var(--muted)">:' + esc(String(s.port)) + '</span></div>'
      + latency
      + '<div class="svc-detail">' + esc(s.detail || '') + '</div>';
    grid.appendChild(card);
  });
}

function renderGit(git) {
  const bar = document.getElementById('git-bar');
  if (!git) { bar.style.display = 'none'; return; }
  bar.style.display = 'flex';
  const dirtyBadge = git.dirty_files > 0
    ? '<span class="badge warning">' + esc(git.dirty_files + ' uncommitted') + '</span>'
    : '<span class="badge ok">clean</span>';
  bar.innerHTML = '<div class="git-item"><span class="git-label">Branch</span>' + esc(git.branch) + '</div>'
    + '<div class="git-item"><span class="git-label">Last Commit</span>' + esc(git.last_commit) + '</div>'
    + '<div class="git-item"><span class="git-label">Working Tree</span>' + dirtyBadge + '</div>';
}

function renderAgents(agents) {
  const procs = document.getElementById('agent-procs');
  procs.textContent = '';
  if (agents.running_agents.length === 0) {
    procs.innerHTML = '<div class="no-data">No Claude sessions running</div>';
  } else {
    agents.running_agents.forEach(function(a) {
      const card = document.createElement('div');
      card.className = 'session-card';
      const s = a.session || {};
      const activity = s.activity || [];
      const lastAct = activity.length > 0 ? activity[activity.length - 1] : null;
      const summary = lastAct ? (lastAct.text || (lastAct.tools || []).join(', ') || '') : 'idle';
      const uptime = s.started_at ? timeSince(s.started_at) : '';

      // -- header --
      var headerParts = [
        '<span class="sess-chevron">\u25b6</span>',
        '<div class="session-meta">',
          '<span class="session-pid">PID ', esc(a.pid), '</span>',
          '<span class="badge running">active</span>',
          '<span class="session-cwd">', esc(s.cwd || ''), '</span>',
          '<span class="session-uptime">', esc(uptime), '</span>',
        '</div>',
        '<span class="agent-stat">CPU ', esc(a.cpu), '% \u00b7 MEM ', esc(a.mem), '%</span>',
        '<span style="font-size:11px;color:var(--muted)">click to expand</span>'
      ];
      const header = document.createElement('div');
      header.className = 'session-header';
      header.innerHTML = headerParts.join('');
      header.addEventListener('click', function() { card.classList.toggle('open'); });

      const summaryDiv = document.createElement('div');
      summaryDiv.className = 'session-summary';
      summaryDiv.textContent = summary;
      header.querySelector('.session-meta').appendChild(summaryDiv);

      // -- body (expanded detail) --
      const body = document.createElement('div');
      body.className = 'session-body';

      // Full command line — always visible when expanded
      if (a.cmd) {
        const cmdDiv = document.createElement('div');
        cmdDiv.style.cssText = 'padding:10px 18px;font-family:monospace;font-size:11px;color:var(--accent);word-break:break-all;white-space:pre-wrap;background:var(--code-bg);border-bottom:1px solid var(--border)';
        cmdDiv.textContent = a.cmd;
        body.appendChild(cmdDiv);
      }

      // Session ID
      if (s.session_id) {
        const sid = document.createElement('div');
        sid.style.cssText = 'padding:6px 18px;font-size:11px;color:var(--muted);border-bottom:1px solid var(--border)';
        sid.textContent = 'Session: ' + s.session_id;
        body.appendChild(sid);
      }

      // Activity feed
      const ul = document.createElement('ul');
      ul.className = 'activity-feed';
      activity.forEach(function(act) {
        const li = document.createElement('li');
        li.className = 'activity-item';
        const tsSpan = document.createElement('span');
        tsSpan.className = 'activity-ts';
        tsSpan.textContent = act.ts ? act.ts.substring(11) : '';
        li.appendChild(tsSpan);
        if (act.type === 'user') {
          const tag = document.createElement('span');
          tag.className = 'activity-user';
          tag.textContent = 'USER';
          li.appendChild(tag);
          li.appendChild(document.createTextNode(' ' + (act.text || '')));
        } else {
          (act.tools || []).forEach(function(t) {
            const tag = document.createElement('span');
            tag.className = 'activity-tool';
            tag.textContent = t;
            li.appendChild(tag);
          });
          if (act.text) {
            const txt = document.createElement('span');
            txt.className = 'activity-text';
            txt.textContent = act.text;
            li.appendChild(txt);
          }
        }
        ul.appendChild(li);
      });
      if (activity.length === 0) {
        const li = document.createElement('li');
        li.className = 'activity-item';
        li.style.color = 'var(--muted)';
        li.textContent = 'No session activity found \u2014 JSONL log may not exist for this process';
        ul.appendChild(li);
      }
      body.appendChild(ul);

      card.appendChild(header);
      card.appendChild(body);
      procs.appendChild(card);
    });
  }

  const jobs = document.getElementById('deploy-jobs');
  jobs.textContent = '';
  if (agents.deploy_jobs.length === 0) {
    jobs.innerHTML = '<div class="no-data">No active deploy jobs</div>';
  } else {
    agents.deploy_jobs.forEach(j => {
      const cls = j.status === 'running' ? 'running' : j.status === 'done' ? 'ok' : 'warning';
      const row = document.createElement('div');
      row.className = 'agent-proc';
      row.innerHTML = '<span class="badge ' + cls + '">' + esc(j.status) + '</span>'
        + '<span style="flex:1;font-size:13px">' + esc(j.title) + '</span>'
        + '<span class="agent-stat">' + esc(j.id.substring(0,8)) + '</span>';
      jobs.appendChild(row);
    });
  }

  const ms = document.getElementById('milestones');
  ms.textContent = '';
  if (agents.milestones.length === 0) {
    ms.innerHTML = '<div class="no-data">No recent milestones</div>';
  } else {
    agents.milestones.forEach(m => {
      const item = document.createElement('div');
      item.className = 'milestone-item';
      item.innerHTML = '<span class="milestone-sha">' + esc(m.sha) + '</span>'
        + '<span class="milestone-msg">' + esc(m.message) + '</span>';
      ms.appendChild(item);
    });
  }
}

// ── Extraction workbench ─────────────────────────────────────────────────────
let _extLoaded = false;
let _extFixtures = [];
let _extPolling = null;

async function loadExtraction() {
  if (_extLoaded) return;
  _extLoaded = true;
  try {
    const resp = await fetch('/api/extraction/fixtures');
    _extFixtures = await resp.json();
    populateFixtureSelect();
    renderFixtureTable();
    // Load tickers for custom mode
    const tr = await fetch('/api/extraction/tickers');
    const tickers = await tr.json();
    const sel = document.getElementById('ext-ticker');
    tickers.forEach(function(t) {
      const o = document.createElement('option');
      o.value = t; o.textContent = t;
      sel.appendChild(o);
    });
  } catch (e) {
    console.error('Failed to load extraction data', e);
  }
}

function populateFixtureSelect() {
  const sel = document.getElementById('ext-fixture');
  sel.textContent = '';
  _extFixtures.forEach(function(f) {
    const o = document.createElement('option');
    o.value = f.name;
    o.textContent = f.ticker + ' ' + f.period_type + ' ' + f.period_end + ' (' + f.currency + ')';
    sel.appendChild(o);
  });
}

function renderFixtureTable() {
  const body = document.getElementById('ext-fixtures-body');
  body.textContent = '';
  _extFixtures.forEach(function(f) {
    const tr = document.createElement('tr');
    tr.style.cursor = 'pointer';
    tr.addEventListener('click', function() {
      document.getElementById('ext-source').value = 'fixture';
      onExtSourceChange();
      document.getElementById('ext-fixture').value = f.name;
    });
    tr.innerHTML = '<td>' + esc(f.name) + '</td>'
      + '<td>' + esc(f.ticker) + '</td>'
      + '<td>' + esc(f.period_type) + '</td>'
      + '<td>' + esc(f.period_end) + '</td>'
      + '<td>' + esc(f.currency) + '</td>'
      + '<td>' + esc(f.scale) + '</td>'
      + '<td>' + f.metric_count + '</td>'
      + '<td>' + (f.pdf_exists ? '<span class="badge ok">' + f.pdf_size_mb + 'MB</span>' : '<span class="badge critical">missing</span>') + '</td>';
    body.appendChild(tr);
  });
}

function onExtSourceChange() {
  const mode = document.getElementById('ext-source').value;
  document.getElementById('ext-fixture-label').style.display = mode === 'fixture' ? '' : 'none';
  document.getElementById('ext-ticker-label').style.display = mode === 'custom' ? '' : 'none';
  document.getElementById('ext-pdf-label').style.display = mode === 'custom' ? '' : 'none';
}

async function onExtTickerChange() {
  const ticker = document.getElementById('ext-ticker').value;
  const sel = document.getElementById('ext-pdf');
  sel.textContent = '';
  sel.innerHTML = '<option value="">Loading...</option>';
  try {
    const resp = await fetch('/api/extraction/pdfs?ticker=' + encodeURIComponent(ticker));
    const pdfs = await resp.json();
    sel.textContent = '';
    pdfs.forEach(function(p) {
      const o = document.createElement('option');
      o.value = p.path;
      o.textContent = p.name + ' (' + p.size_mb + 'MB)';
      sel.appendChild(o);
    });
  } catch (e) {
    sel.innerHTML = '<option value="">Error loading PDFs</option>';
  }
}

function fmtNum(n) {
  if (n == null) return '\u2014';
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(0) + 'K';
  return String(n);
}

async function runExtraction() {
  const btn = document.getElementById('ext-run-btn');
  btn.disabled = true;
  btn.textContent = '\u23f3 Running...';

  const mode = document.getElementById('ext-source').value;
  const config = {
    model: document.getElementById('ext-model').value,
    extraction_url: document.getElementById('ext-url').value,
    force_pymupdf: document.getElementById('ext-force-pymupdf').checked,
    skip_narrative: document.getElementById('ext-skip-narrative').checked,
    no_parallel: document.getElementById('ext-no-parallel').checked,
    no_filter_rows: document.getElementById('ext-no-filter').checked,
    no_skip_redundant: document.getElementById('ext-no-skip-redundant').checked,
  };

  _lastExtConfig = config;
  const body = {config: config};
  if (mode === 'fixture') {
    body.fixture_name = document.getElementById('ext-fixture').value;
  } else {
    body.pdf_path = document.getElementById('ext-pdf').value;
  }

  // Show PDF viewer immediately
  const results = document.getElementById('ext-results');
  results.style.display = 'block';
  if (body.fixture_name) {
    const f = _extFixtures.find(function(x) { return x.name === body.fixture_name; });
    if (f && f.pdf_path) {
      document.getElementById('ext-pdf-viewer').src = '/api/pdf/' + f.pdf_path;
    }
  } else if (body.pdf_path) {
    document.getElementById('ext-pdf-viewer').src = '/api/pdf/' + body.pdf_path;
  }

  document.getElementById('ext-log').textContent = 'Starting extraction...';
  document.getElementById('ext-metrics-body').textContent = '';
  document.getElementById('ext-accuracy').textContent = '';
  document.getElementById('ext-raw').textContent = '';
  document.getElementById('ext-status-badge').textContent = 'running';
  document.getElementById('ext-status-badge').className = 'badge running';

  try {
    const resp = await fetch('/api/extraction/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (data.ok) {
      pollExtractionJob(data.job_id);
    } else {
      showExtError(data.error || 'Failed to start');
      btn.disabled = false;
      btn.textContent = '\u25b6 Run Extraction';
    }
  } catch (e) {
    showExtError(String(e));
    btn.disabled = false;
    btn.textContent = '\u25b6 Run Extraction';
  }
}

var _activeJobId = null;

function pollExtractionJob(jobId) {
  _activeJobId = jobId;
  if (_extPolling) clearInterval(_extPolling);

  // Show cancel button
  var btn = document.getElementById('ext-run-btn');
  btn.disabled = false;
  btn.textContent = '\u25a0 Cancel';
  btn.onclick = function() { cancelExtractionJob(jobId); };

  _extPolling = setInterval(async function() {
    try {
      const resp = await fetch('/api/extraction/job/' + encodeURIComponent(jobId));
      const job = await resp.json();
      renderExtLog(job.output || []);
      if (job.status === 'done' || job.status === 'error' || job.status === 'cancelled') {
        clearInterval(_extPolling);
        _extPolling = null;
        _activeJobId = null;
        btn.disabled = false;
        btn.textContent = '\u25b6 Run Extraction';
        btn.onclick = runExtraction;
        if (job.status === 'done') {
          renderExtResults(job);
          initChat(jobId);
        } else {
          showExtError(job.error || 'Extraction failed');
        }
      }
    } catch (e) {
      clearInterval(_extPolling);
      _extPolling = null;
      _activeJobId = null;
    }
  }, 2000);
}

async function cancelExtractionJob(jobId) {
  var btn = document.getElementById('ext-run-btn');
  btn.disabled = true;
  btn.textContent = 'Cancelling...';
  try {
    await fetch('/api/extraction/cancel/' + encodeURIComponent(jobId), {method: 'POST'});
  } catch (e) {
    // Poll will pick up the final state
  }
}

function renderExtLog(lines) {
  const el = document.getElementById('ext-log');
  el.textContent = lines.join('\n');
  el.scrollTop = el.scrollHeight;
}

function showExtError(msg) {
  document.getElementById('ext-status-badge').textContent = 'error';
  document.getElementById('ext-status-badge').className = 'badge critical';
  document.getElementById('ext-log').textContent += '\nERROR: ' + msg;
}

function _parseProvPage(prov) {
  // Parse "cash_flow:page_3:Operating cash flow" → page number 3
  if (!prov) return null;
  var m = prov.match(/page_(\d+)/);
  return m ? parseInt(m[1], 10) : null;
}

function _navigatePdfToPage(pageNum) {
  var viewer = document.getElementById('ext-pdf-viewer');
  if (!viewer || !viewer.src || viewer.src === 'about:blank') return;
  // PDF.js and browser PDF viewers support #page=N fragment
  var base = viewer.src.split('#')[0];
  viewer.src = base + '#page=' + pageNum;
}

var _periodTypes = {A: 'Annual', H: 'Half-year', Q: 'Quarterly'};

function _showPeriodInTable(payload, fixturePeriod) {
  // Always show period inside the comparison table header
  var row = document.getElementById('ext-period-row');
  var cell = document.getElementById('ext-period-cell');
  if (!payload) { row.style.display = 'none'; return; }

  var pt = payload.period_type;
  var pe = String(payload.period_end || '');
  var scale = payload.scale || '?';
  var currency = payload.currency || '?';
  var conf = payload.confidence_metrics;

  var parts = [];
  parts.push('<b>Period:</b> ' + esc(pt ? (_periodTypes[pt] || pt) : '?') + ' ending ' + esc(pe || '?'));
  parts.push('<b>Currency:</b> ' + esc(currency));
  parts.push('<b>Scale:</b> ' + esc(scale));
  if (conf != null) {
    var confPct = Math.round(conf * 100);
    var confCls = confPct >= 70 ? 'ok' : confPct >= 40 ? 'warning' : 'critical';
    parts.push('<b>Confidence:</b> <span style="color:var(--' + confCls + ')">' + confPct + '%</span>');
  }

  if (fixturePeriod && fixturePeriod.period_end) {
    var mismatch = (pt !== fixturePeriod.period_type || pe !== fixturePeriod.period_end);
    if (mismatch) {
      var fixType = fixturePeriod.period_type ? (_periodTypes[fixturePeriod.period_type] || fixturePeriod.period_type) : '?';
      parts.push('<span style="color:var(--warning);font-weight:600">\u26a0 Expected: ' + esc(fixType) + ' ending ' + esc(fixturePeriod.period_end) + '</span>');
    }
  }

  cell.innerHTML = parts.join(' &nbsp;\u00b7&nbsp; ');
  row.style.display = '';
}

function renderExtResults(job) {
  const result = job.result;
  const comparison = job.comparison;

  document.getElementById('ext-status-badge').textContent = result.status;
  document.getElementById('ext-status-badge').className = 'badge ' + (result.status === 'ok' ? 'ok' : 'warning');
  document.getElementById('ext-elapsed').textContent = result.elapsed_s + 's';

  // Raw payload
  document.getElementById('ext-raw').textContent = JSON.stringify(result.payload, null, 2);

  // Period bar
  var periodBar = document.getElementById('ext-period-bar');
  periodBar.textContent = '';
  if (comparison && comparison.period) {
    var ep = comparison.period;
    var fp = comparison.fixture_period || {};
    var parts = [];

    // Extracted period
    var extType = ep.period_type ? (_periodTypes[ep.period_type] || ep.period_type) : '?';
    parts.push('<span><span class="period-label">Extracted:</span> ' + esc(extType) + ' ending ' + esc(ep.period_end || '?') + '</span>');

    // Expected period from fixture
    if (fp.period_end) {
      var fixType = fp.period_type ? (_periodTypes[fp.period_type] || fp.period_type) : '?';
      var mismatch = (ep.period_type !== fp.period_type || ep.period_end !== fp.period_end);
      var cls = mismatch ? 'period-mismatch' : 'period-label';
      parts.push('<span><span class="' + cls + '">Expected:</span> ' + esc(fixType) + ' ending ' + esc(fp.period_end) + (mismatch ? ' \u26a0 MISMATCH' : '') + '</span>');
    }

    // Currency
    if (fp.currency) parts.push('<span><span class="period-label">Currency:</span> ' + esc(fp.currency) + '</span>');

    // Confidence
    if (ep.confidence_metrics != null) {
      var conf = Math.round(ep.confidence_metrics * 100);
      var confCls = conf >= 70 ? 'ok' : conf >= 40 ? 'warning' : 'critical';
      parts.push('<span><span class="period-label">LLM Confidence:</span> <span style="color:var(--' + confCls + ')">' + conf + '%</span></span>');
    }

    periodBar.innerHTML = parts.join('');
  } else if (result.payload) {
    // No fixture — show extracted period only
    var pt = result.payload.period_type;
    var pe = result.payload.period_end;
    var conf = result.payload.confidence_metrics;
    var parts = [];
    if (pt || pe) parts.push('<span><span class="period-label">Period:</span> ' + esc(pt ? (_periodTypes[pt] || pt) : '?') + ' ending ' + esc(String(pe || '?')) + '</span>');
    if (conf != null) {
      var confPct = Math.round(conf * 100);
      parts.push('<span><span class="period-label">LLM Confidence:</span> ' + confPct + '%</span>');
    }
    periodBar.innerHTML = parts.join('');
  }

  // Period row in table — always show when payload exists
  _showPeriodInTable(result.payload, comparison ? comparison.fixture_period : null);

  // Metrics comparison
  if (comparison) {
    const accPct = Math.round(comparison.accuracy * 100);
    const cls = accPct >= 85 ? 'ok' : accPct >= 70 ? 'warning' : 'critical';
    document.getElementById('ext-accuracy').innerHTML =
      '<span style="color:var(--' + cls + ')">' + accPct + '%</span>'
      + '<span style="font-size:14px;color:var(--muted);margin-left:8px">'
      + comparison.matches + '/' + comparison.total + ' metrics match</span>';

    const body = document.getElementById('ext-metrics-body');
    body.textContent = '';
    Object.keys(comparison.comparisons).forEach(function(field) {
      const c = comparison.comparisons[field];
      const tr = document.createElement('tr');

      // Status + retry button for misses
      var statusCell = document.createElement('td');
      var statusSpan = document.createElement('span');
      statusSpan.className = c.match ? 'metric-match' : 'metric-miss';
      statusSpan.textContent = c.match ? '\u2713' : '\u2717';
      statusCell.appendChild(statusSpan);
      if (!c.match) {
        var retryBtn = document.createElement('button');
        retryBtn.className = 'retry-btn';
        retryBtn.textContent = '\u21bb retry';
        retryBtn.title = 'Re-run extraction for just the ' + field + ' table';
        retryBtn.addEventListener('click', (function(f) {
          return function() { retryMetric(f); };
        })(field));
        statusCell.appendChild(document.createTextNode(' '));
        statusCell.appendChild(retryBtn);
      }

      // Diff
      var diffCell = document.createElement('td');
      if (c.pct_diff != null) {
        var pctSpan = document.createElement('span');
        pctSpan.className = c.match ? 'metric-match' : 'metric-miss';
        pctSpan.textContent = (c.pct_diff * 100).toFixed(2) + '%';
        diffCell.appendChild(pctSpan);
      } else {
        var nullSpan = document.createElement('span');
        nullSpan.className = 'metric-null';
        nullSpan.textContent = c.status;
        diffCell.appendChild(nullSpan);
      }

      // Provenance (clickable — navigates PDF to source page)
      var provCell = document.createElement('td');
      if (c.provenance) {
        var provSpan = document.createElement('span');
        provSpan.className = 'prov-link';
        // Show short form: "cash_flow:p3" instead of full string
        var shortProv = c.provenance.replace(/page_/g, 'p').replace(/:unknown/g, '');
        provSpan.textContent = shortProv;
        provSpan.title = c.provenance + ' \u2014 click to jump to source page in PDF';
        var pageNum = _parseProvPage(c.provenance);
        if (pageNum) {
          provSpan.addEventListener('click', (function(pg) {
            return function() { _navigatePdfToPage(pg); };
          })(pageNum));
        }
        provCell.appendChild(provSpan);
      } else {
        provCell.textContent = '\u2014';
        provCell.style.color = 'var(--muted)';
      }

      // Build row
      var metricCell = document.createElement('td');
      metricCell.textContent = field;
      var extractedCell = document.createElement('td');
      extractedCell.style.fontFamily = 'monospace';
      extractedCell.textContent = fmtNum(c.extracted);
      var expectedCell = document.createElement('td');
      expectedCell.style.fontFamily = 'monospace';
      expectedCell.textContent = fmtNum(c.expected);

      // Highlight mismatches
      if (!c.match) {
        tr.style.background = 'rgba(248,81,73,.06)';
      }

      tr.appendChild(metricCell);
      tr.appendChild(extractedCell);
      tr.appendChild(expectedCell);
      tr.appendChild(diffCell);
      tr.appendChild(provCell);
      tr.appendChild(statusCell);
      body.appendChild(tr);
    });
  } else if (result.payload) {
    // No fixture comparison — show raw extracted values with provenance
    document.getElementById('ext-accuracy').textContent = 'No fixture for comparison';
    const body = document.getElementById('ext-metrics-body');
    body.textContent = '';
    var prov = result.payload.provenance || {};
    var mf = ['revenue','ebit','np_attributable','operating_cf','investing_cf','financing_cf','capex','cash_end','net_debt','shares_outstanding'];
    mf.forEach(function(field) {
      const val = result.payload[field];
      const tr = document.createElement('tr');

      var metricCell = document.createElement('td');
      metricCell.textContent = field;
      var valCell = document.createElement('td');
      valCell.style.fontFamily = 'monospace';
      valCell.textContent = fmtNum(val);
      var emptyCell1 = document.createElement('td');
      emptyCell1.textContent = '\u2014';
      var emptyCell2 = document.createElement('td');
      emptyCell2.textContent = '\u2014';

      // Provenance
      var provCell = document.createElement('td');
      var fieldProv = prov[field] || '';
      if (fieldProv) {
        var provSpan = document.createElement('span');
        provSpan.className = 'prov-link';
        provSpan.textContent = fieldProv.replace(/page_/g, 'p').replace(/:unknown/g, '');
        provSpan.title = fieldProv + ' \u2014 click to jump to source page in PDF';
        var pageNum = _parseProvPage(fieldProv);
        if (pageNum) {
          provSpan.addEventListener('click', (function(pg) {
            return function() { _navigatePdfToPage(pg); };
          })(pageNum));
        }
        provCell.appendChild(provSpan);
      } else {
        provCell.textContent = '\u2014';
        provCell.style.color = 'var(--muted)';
      }

      var emptyCell3 = document.createElement('td');
      emptyCell3.textContent = '\u2014';

      tr.appendChild(metricCell);
      tr.appendChild(valCell);
      tr.appendChild(emptyCell1);
      tr.appendChild(emptyCell2);
      tr.appendChild(provCell);
      tr.appendChild(emptyCell3);
      body.appendChild(tr);
    });
  }

  // Render gaps
  renderExtGaps(job);
  // Render raw tables from diagnostics
  renderRawTables(job);
  // Load history if we have a fixture
  var fixtureSel = document.getElementById('ext-fixture');
  if (fixtureSel && fixtureSel.value) {
    loadExtHistory(fixtureSel.value);
  }
}

// ── Retry per metric ────────────────────────────────────────────────────────
var _retryPolling = null;

function retryMetric(metric) {
  var pdfPath = '';
  // Get PDF path from current job or fixture
  var fixtureSel = document.getElementById('ext-fixture');
  if (fixtureSel && fixtureSel.value && _extFixtures) {
    var f = _extFixtures.find(function(x) { return x.name === fixtureSel.value; });
    if (f) pdfPath = f.pdf_path;
  }
  if (!pdfPath) {
    var pdfInput = document.getElementById('ext-pdf');
    if (pdfInput) pdfPath = pdfInput.value;
  }
  if (!pdfPath) return;

  var panel = document.getElementById('ext-retry-panel');
  panel.style.display = 'block';
  document.getElementById('ext-retry-status').textContent = 'running ' + metric;
  document.getElementById('ext-retry-status').className = 'badge running';
  document.getElementById('ext-retry-log').textContent = 'Retrying ' + metric + '...';
  document.getElementById('ext-retry-raw').textContent = '';

  fetch('/api/extraction/retry', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({pdf_path: pdfPath, metric: metric, config: _lastExtConfig || {}}),
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (data.ok) pollRetryJob(data.job_id);
  });
}

function pollRetryJob(jobId) {
  if (_retryPolling) clearInterval(_retryPolling);
  _retryPolling = setInterval(async function() {
    try {
      var resp = await fetch('/api/extraction/job/' + encodeURIComponent(jobId));
      var job = await resp.json();
      if (job.output) document.getElementById('ext-retry-log').textContent = job.output.join('\\n');
      if (job.status === 'done' || job.status === 'error') {
        clearInterval(_retryPolling);
        _retryPolling = null;
        var badge = document.getElementById('ext-retry-status');
        badge.textContent = job.status;
        badge.className = 'badge ' + (job.status === 'done' ? 'ok' : 'critical');
        if (job.result) {
          document.getElementById('ext-retry-raw').textContent = JSON.stringify(job.result, null, 2);
        }
      }
    } catch (e) {
      clearInterval(_retryPolling);
      _retryPolling = null;
    }
  }, 2000);
}

var _lastExtConfig = {};

// ── Gaps renderer ───────────────────────────────────────────────────────────
function renderExtGaps(job) {
  var gaps = (job.comparison && job.comparison.gaps) || job.gaps || [];
  var container = document.getElementById('ext-gaps');
  var countBadge = document.getElementById('ext-gap-count');
  container.textContent = '';
  countBadge.textContent = gaps.length;
  countBadge.className = 'badge ' + (gaps.length === 0 ? 'ok' : gaps.length <= 3 ? 'warning' : 'critical');

  if (gaps.length === 0) {
    container.textContent = 'No quality gaps detected';
    container.style.color = 'var(--muted)';
    return;
  }
  container.style.color = '';
  gaps.forEach(function(g) {
    var div = document.createElement('div');
    div.className = 'gap-item';
    var typeSpan = document.createElement('span');
    var warnTypes = ['derived', 'unknown_row'];
    typeSpan.className = 'gap-type' + (warnTypes.indexOf(g.type) >= 0 ? ' warn' : '');
    typeSpan.textContent = g.type;
    var fieldSpan = document.createElement('span');
    fieldSpan.className = 'gap-field';
    fieldSpan.textContent = g.field;
    var detailSpan = document.createElement('span');
    detailSpan.textContent = g.detail;
    detailSpan.style.color = 'var(--muted)';
    div.appendChild(typeSpan);
    div.appendChild(fieldSpan);
    div.appendChild(detailSpan);
    container.appendChild(div);
  });
}

// ── History renderer ────────────────────────────────────────────────────────
function loadExtHistory(fixtureName) {
  fetch('/api/extraction/history/' + encodeURIComponent(fixtureName))
    .then(function(r) { return r.json(); })
    .then(function(runs) { renderExtHistory(runs); });
}

function renderExtHistory(runs) {
  var container = document.getElementById('ext-history');
  container.textContent = '';
  if (!runs || runs.length === 0) {
    container.textContent = 'No previous runs';
    container.style.color = 'var(--muted)';
    return;
  }
  container.style.color = '';
  // Show most recent first
  runs.slice().reverse().forEach(function(run) {
    var row = document.createElement('div');
    row.className = 'hist-row';
    var acc = run.accuracy != null ? Math.round(run.accuracy * 100) : '?';
    var accCls = acc >= 85 ? 'ok' : acc >= 70 ? 'warning' : 'critical';

    var accSpan = document.createElement('span');
    accSpan.className = 'hist-acc';
    accSpan.style.color = 'var(--' + accCls + ')';
    accSpan.textContent = acc + '%';

    var bar = document.createElement('span');
    bar.className = 'hist-bar';
    var fill = document.createElement('span');
    fill.className = 'hist-bar-fill';
    fill.style.width = (typeof acc === 'number' ? acc : 0) + '%';
    fill.style.background = 'var(--' + accCls + ')';
    bar.appendChild(fill);

    var info = document.createElement('span');
    info.style.cssText = 'font-size:11px;color:var(--muted);flex:1';
    var ts = (run.timestamp || '').substring(0, 16).replace('T', ' ');
    info.textContent = ts + ' \u00b7 ' + (run.elapsed_s || '?') + 's'
      + ' \u00b7 ' + (run.matches || 0) + '/' + (run.total || 0)
      + ' \u00b7 scale:' + (run.scale || '?')
      + (run.gap_count ? ' \u00b7 ' + run.gap_count + ' gaps' : '');

    row.appendChild(accSpan);
    row.appendChild(bar);
    row.appendChild(info);
    container.appendChild(row);
  });
}

// ── Raw tables viewer ───────────────────────────────────────────────────────
function renderRawTables(job) {
  var container = document.getElementById('ext-raw-tables');
  container.textContent = '';
  var diag = (job.result && job.result.diagnostics) || {};
  var tables = diag.raw_tables || {};
  var keys = Object.keys(tables);
  if (keys.length === 0) {
    container.textContent = 'No table data captured (diagnostics may not have run)';
    container.style.color = 'var(--muted)';
    return;
  }
  container.style.color = '';
  keys.forEach(function(label) {
    var t = tables[label];
    var block = document.createElement('details');
    block.className = 'raw-table-block';
    var summary = document.createElement('summary');
    summary.textContent = label + ' (page ' + (t.page || '?') + ', ' + (t.rows || '?') + ' rows)';
    var pre = document.createElement('pre');
    pre.className = 'raw-table-md';
    pre.textContent = t.markdown || '(empty)';
    block.appendChild(summary);
    block.appendChild(pre);
    container.appendChild(block);
  });

  // Show scale + table stats in period bar if diagnostics available
  if (diag.scale) {
    var periodBar = document.getElementById('ext-period-bar');
    var scaleSpan = document.createElement('span');
    var match = diag.scale.match;
    var label = document.createElement('span');
    label.className = 'period-label';
    label.textContent = 'Scale:';
    scaleSpan.appendChild(label);
    scaleSpan.appendChild(document.createTextNode(' ' + esc(diag.scale.effective)
      + ' (header:' + esc(diag.scale.header_detected) + ', LLM:' + esc(diag.scale.llm_detected) + ')'));
    if (!match) {
      var warn = document.createElement('span');
      warn.className = 'period-mismatch';
      warn.textContent = ' \u26a0 MISMATCH';
      scaleSpan.appendChild(warn);
    }
    periodBar.appendChild(scaleSpan);

    var tableSpan = document.createElement('span');
    tableSpan.textContent = diag.labelled_count + '/' + diag.table_count + ' tables labelled';
    var tl = document.createElement('span');
    tl.className = 'period-label';
    tl.textContent = 'Tables:';
    tableSpan.prepend(document.createTextNode(' '));
    tableSpan.prepend(tl);
    periodBar.appendChild(tableSpan);
  }
}

// ── Chat with Claude ─────────────────────────────────────────────────────────
var _chatId = null;
var _lastJobId = null;

function initChat(jobId) {
  _lastJobId = jobId;
  document.getElementById('ext-chat-panel').style.display = 'block';
  document.getElementById('ext-chat-messages').textContent = '';
  document.getElementById('ext-chat-status').textContent = 'starting session...';
  document.getElementById('ext-chat-status').className = 'badge running';
  document.getElementById('ext-chat-send').disabled = true;
  _addChatMsg('assistant thinking', 'Starting Claude session and loading extraction context...');

  fetch('/api/extraction/chat/start', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({job_id: jobId}),
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (data.ok) {
      _chatId = data.chat_id;
      // Poll for Claude's initial response (context acknowledgment)
      var initPoll = setInterval(function() {
        fetch('/api/extraction/chat/poll/' + encodeURIComponent(_chatId))
          .then(function(r) { return r.json(); })
          .then(function(poll) {
            if (poll.status === 'ready') {
              clearInterval(initPoll);
              // Clear the "loading" message and show Claude's summary
              document.getElementById('ext-chat-messages').textContent = '';
              var msgs = poll.messages || [];
              msgs.forEach(function(m) {
                if (m.role === 'assistant') _addChatMsg('assistant', m.text);
              });
              document.getElementById('ext-chat-status').textContent = 'ready';
              document.getElementById('ext-chat-status').className = 'badge ok';
              document.getElementById('ext-chat-send').disabled = false;
              document.getElementById('ext-chat-input').focus();
            }
          });
      }, 2000);
    } else {
      document.getElementById('ext-chat-messages').textContent = '';
      document.getElementById('ext-chat-status').textContent = 'error';
      document.getElementById('ext-chat-status').className = 'badge critical';
      _addChatMsg('assistant', 'Failed to start: ' + (data.error || 'unknown'));
    }
  });
}

function _addChatMsg(role, text) {
  var container = document.getElementById('ext-chat-messages');
  var div = document.createElement('div');
  div.className = 'ext-chat-msg ' + role;
  div.textContent = text;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function sendChatMessage() {
  if (!_chatId) return;
  var input = document.getElementById('ext-chat-input');
  var msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  _addChatMsg('user', msg);
  var thinking = _addChatMsg('assistant thinking', 'Thinking...');
  document.getElementById('ext-chat-status').textContent = 'thinking';
  document.getElementById('ext-chat-status').className = 'badge running';
  document.getElementById('ext-chat-send').disabled = true;

  fetch('/api/extraction/chat/send', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({chat_id: _chatId, message: msg}),
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (!data.ok) {
      thinking.remove();
      _addChatMsg('assistant', 'Error: ' + (data.error || 'unknown'));
      document.getElementById('ext-chat-send').disabled = false;
      return;
    }
    // Poll for response
    var _chatPoll = setInterval(function() {
      fetch('/api/extraction/chat/poll/' + encodeURIComponent(_chatId))
        .then(function(r) { return r.json(); })
        .then(function(poll) {
          if (poll.status === 'ready') {
            clearInterval(_chatPoll);
            thinking.remove();
            // Show the last assistant message
            var msgs = poll.messages || [];
            var last = msgs[msgs.length - 1];
            if (last && last.role === 'assistant') {
              _addChatMsg('assistant', last.text);
            }
            document.getElementById('ext-chat-status').textContent = 'ready';
            document.getElementById('ext-chat-status').className = 'badge ok';
            document.getElementById('ext-chat-send').disabled = false;
            document.getElementById('ext-chat-input').focus();
          }
        });
    }, 1500);
  }).catch(function(e) {
    thinking.remove();
    _addChatMsg('assistant', 'Error: ' + String(e));
    document.getElementById('ext-chat-send').disabled = false;
  });
}

// Enter key sends message
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && document.activeElement && document.activeElement.id === 'ext-chat-input') {
    e.preventDefault();
    sendChatMessage();
  }
});

// ── Monitor scan ─────────────────────────────────────────────────────────────
var _scanPolling = null;

function runMonitorScan() {
  var btn = document.getElementById('scan-btn');
  var status = document.getElementById('scan-status');
  btn.disabled = true;
  btn.textContent = '\u23f3 Scanning...';
  status.textContent = 'Running 5 agents on new commits...';

  fetch('/api/monitors/scan', {method: 'POST'})
    .then(function(r) { return r.json(); })
    .then(function(data) {
      if (data.ok) {
        // Poll for completion
        _scanPolling = setInterval(function() {
          fetch('/api/monitors/status')
            .then(function(r) { return r.json(); })
            .then(function(s) {
              status.textContent = s.status || 'running...';
              if (s.done) {
                clearInterval(_scanPolling);
                _scanPolling = null;
                btn.disabled = false;
                btn.textContent = '\ud83d\udd0d Scan for new bugs';
                status.textContent = s.status || 'Scan complete';
                // Reload bugs
                loadData();
              }
            });
        }, 3000);
      } else {
        btn.disabled = false;
        btn.textContent = '\ud83d\udd0d Scan for new bugs';
        status.textContent = 'Error: ' + (data.error || 'unknown');
      }
    });
}

function refreshAll() {
  loadData();
  if (document.getElementById('page-system').classList.contains('active')) loadSystem();
}

loadData().then(loadJobs);
setInterval(loadData, 30000);
setInterval(function() { if (document.getElementById('page-system').classList.contains('active')) loadSystem(); }, 15000);
// Enter key for drawer chat
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && document.activeElement && document.activeElement.id === 'drawer-chat-input') {
    e.preventDefault();
    drawerSend();
  }
});
</script>

<!-- Floating chat button + drawer -->
<button class="chat-fab" id="chat-fab" onclick="toggleDrawer()" title="Chat with Claude">&#x1f4ac;</button>
<div class="chat-drawer" id="chat-drawer">
  <div class="chat-drawer-header">
    <span style="font-size:12px;font-weight:600;color:var(--text);flex-shrink:0">Claude</span>
    <span class="badge" id="drawer-status">idle</span>
  </div>
  <div class="chat-drawer-messages" id="drawer-messages"></div>
  <div class="chat-drawer-input">
    <button class="chat-screenshot-btn" onclick="drawerScreenshot()" title="Attach screenshot">&#x1f4f7;</button>
    <input type="text" id="drawer-chat-input" placeholder="Ask about this page..." autocomplete="off">
    <button id="drawer-send-btn" onclick="drawerSend()">Send</button>
  </div>
</div>

<script>
var _drawerOpen = false;
var _drawerChatId = null;
var _drawerScreenshot = null; // base64 PNG

function toggleDrawer() {
  _drawerOpen = !_drawerOpen;
  document.getElementById('chat-drawer').classList.toggle('open', _drawerOpen);
  if (_drawerOpen) {
    refreshDrawerSessions();
    document.getElementById('drawer-chat-input').focus();
  }
}

function refreshDrawerSessions() {
  fetch('/api/system').then(function(r) { return r.json(); }).then(function(data) {
    var agents = data.agents || {};
    var running = agents.running_agents || [];
    var sel = document.getElementById('drawer-session-select');
    // Keep "new" option, clear the rest
    while (sel.options.length > 1) sel.remove(1);
    running.forEach(function(a) {
      var s = a.session || {};
      var label = 'PID ' + a.pid;
      if (s.cwd) label += ' \u2014 ' + s.cwd.split('/').pop();
      var lastAct = (s.activity || []).slice(-1)[0];
      if (lastAct && lastAct.text) label += ' (' + lastAct.text.substring(0, 40) + ')';
      var opt = document.createElement('option');
      opt.value = a.pid;
      opt.textContent = label;
      sel.appendChild(opt);
    });
  });
}

function _drawerAddMsg(role, text) {
  var c = document.getElementById('drawer-messages');
  var div = document.createElement('div');
  div.className = 'ext-chat-msg ' + role;
  div.textContent = text;
  c.appendChild(div);
  c.scrollTop = c.scrollHeight;
  return div;
}

function drawerScreenshot() {
  var btn = document.querySelector('.chat-screenshot-btn');
  btn.textContent = '\u23f3';
  html2canvas(document.querySelector('.page.active') || document.body, {
    backgroundColor: '#0d1117', scale: 1, logging: false,
  }).then(function(canvas) {
    _drawerScreenshot = canvas.toDataURL('image/png');
    btn.textContent = '\u2705';
    _drawerAddMsg('user', '[Screenshot attached]');
    setTimeout(function() { btn.textContent = '\ud83d\udcf7'; }, 2000);
  }).catch(function() {
    btn.textContent = '\u274c';
    setTimeout(function() { btn.textContent = '\ud83d\udcf7'; }, 2000);
  });
}

function drawerSend() {
  var input = document.getElementById('drawer-chat-input');
  var msg = input.value.trim();
  if (!msg && !_drawerScreenshot) return;
  input.value = '';

  var fullMsg = msg;
  var screenshotData = _drawerScreenshot;
  _drawerScreenshot = null;

  // Start session if needed
  if (!_drawerChatId) {
    _drawerAddMsg('user', msg || '(screenshot)');
    var thinking = _drawerAddMsg('assistant thinking', 'Starting session...');
    document.getElementById('drawer-status').textContent = 'starting';
    document.getElementById('drawer-status').className = 'badge running';
    document.getElementById('drawer-send-btn').disabled = true;

    // Build context about current page
    var activePage = document.querySelector('.page.active');
    var pageId = activePage ? activePage.id.replace('page-', '') : 'unknown';
    var pageContext = 'The user is on the "' + pageId + '" page of the Tenn Bug Monitor dashboard (http://localhost:8765).';

    var body = {page_context: pageContext, message: fullMsg};
    if (screenshotData) body.screenshot = screenshotData;

    fetch('/api/chat/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    }).then(function(r) { return r.json(); }).then(function(data) {
      if (data.ok) {
        _drawerChatId = data.chat_id;
        document.getElementById('chat-fab').classList.add('has-session');
        _pollDrawerChat(thinking);
      } else {
        thinking.remove();
        _drawerAddMsg('assistant', 'Error: ' + (data.error || 'unknown'));
        document.getElementById('drawer-send-btn').disabled = false;
      }
    });
    return;
  }

  // Existing session — send message
  _drawerAddMsg('user', msg || '(screenshot)');
  var thinking = _drawerAddMsg('assistant thinking', 'Thinking...');
  document.getElementById('drawer-status').textContent = 'thinking';
  document.getElementById('drawer-status').className = 'badge running';
  document.getElementById('drawer-send-btn').disabled = true;

  var body = {chat_id: _drawerChatId, message: fullMsg};
  if (screenshotData) body.screenshot = screenshotData;

  fetch('/api/chat/send', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (data.ok) {
      _pollDrawerChat(thinking);
    } else {
      thinking.remove();
      _drawerAddMsg('assistant', 'Error: ' + (data.error || 'unknown'));
      document.getElementById('drawer-send-btn').disabled = false;
    }
  });
}

function _pollDrawerChat(thinkingEl) {
  var poll = setInterval(function() {
    fetch('/api/chat/poll/' + encodeURIComponent(_drawerChatId))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.status === 'ready') {
          clearInterval(poll);
          thinkingEl.remove();
          var msgs = data.messages || [];
          var last = msgs[msgs.length - 1];
          if (last && last.role === 'assistant') {
            _drawerAddMsg('assistant', last.text);
          }
          document.getElementById('drawer-status').textContent = 'ready';
          document.getElementById('drawer-status').className = 'badge ok';
          document.getElementById('drawer-send-btn').disabled = false;
          document.getElementById('drawer-chat-input').focus();
        }
      });
  }, 1500);
}
</script>
</body>
</html>
"""

_ISSUE_ID_RE = re.compile(r'^[a-f0-9]{40}$')

_DEBATE_SYSTEM_PROMPT = (
    "You are a code-fix debate moderator. You will be given a detected code issue.\n"
    "Propose TWO competing fixes: Agent A (minimal \u2014 smallest safe change) and Agent B\n"
    "(comprehensive \u2014 cleaner abstraction). Then give a verdict on which is better.\n\n"
    "Respond with ONLY a valid JSON object matching this exact schema:\n"
    '{\n'
    '  "agent_a": {"name": "Agent A \u2014 Minimal Fix", "approach": "<one sentence>", "diff": "<unified diff or explanation>"},\n'
    '  "agent_b": {"name": "Agent B \u2014 Comprehensive Fix", "approach": "<one sentence>", "diff": "<unified diff or explanation>"},\n'
    '  "verdict": "<explanation of which is better and why>",\n'
    '  "winning_agent": "a" | "b" | "both" | null\n'
    "}\n"
    "No markdown fences. No preamble. JSON only."
)


def _call_debate_api(agent: str, severity: str, issue_type: str,
                     location: str, detail: str) -> dict:
    """Generate debate via claude CLI. Raises on error."""
    if shutil.which("claude") is None:
        raise RuntimeError("claude CLI not found on PATH")
    user_msg = (
        f"Agent: {agent}\nSeverity: {severity}\nIssue type: {issue_type}\n"
        f"Location: {location}\nDetail: {detail}\n\nPropose two fixes and give a verdict."
    )
    full_prompt = f"{_DEBATE_SYSTEM_PROMPT}\n\n{user_msg}"
    result = subprocess.run(
        ["claude", "--print", "-p", full_prompt],
        capture_output=True, text=True, timeout=120,
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "unknown error")[:300]
        raise RuntimeError(f"claude CLI failed: {err}")
    raw = result.stdout.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def _generate_debate(issue_id: str, agent: str, severity: str,
                     issue_type: str, location: str, detail: str) -> dict:
    """Return debate for issue_id, using cache if available."""
    with _DEBATES_LOCK:
        cached = _load_json_safe(DEBATES_DB) or {}
        if issue_id in cached:
            return cached[issue_id]

    result = _call_debate_api(agent, severity, issue_type, location, detail)
    result["_issue_type"] = issue_type
    result["_location"] = location
    result["_detail"] = detail
    # Ensure title/explanation exist so makeBugCard never gets undefined
    if "title" not in result:
        result["title"] = issue_type.replace("-", " ").title()
    if "explanation" not in result:
        result["explanation"] = detail

    with _DEBATES_LOCK:
        existing = _load_json_safe(DEBATES_DB) or {}
        existing[issue_id] = result
        DEBATES_DB.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    return result


_FIX_ID_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9\-]{0,79}$')
_FIX_ID_SHA1_RE = re.compile(r'^[a-f0-9]{40}$')


_DOC_UPDATE_STEPS = (
    "\n5. Update docs/claude/STATE.md: mark this bug as fixed under the relevant workstream."
    "\n6. If this is a new pattern, append a lesson to docs/claude/lessons.md."
)


def _build_task_string(fix_id: str, fix: dict | None, debates: dict) -> str:
    """Construct the -p task string for the claude subprocess."""
    if fix is not None:
        winning = fix.get("winning_agent")
        if winning is None:
            return (
                f"Investigate and fix the following issue in {fix['file']}:\n\n"
                f"Issue: {fix['title']}\n"
                f"Description: {fix['explanation']}\n\n"
                f"Two approaches have been proposed:\n"
                f"- Agent A: {fix['agent_a']['approach']}\n"
                f"- Agent B: {fix['agent_b']['approach']}\n\n"
                "Steps:\n"
                f"1. Read {fix['file']} and all relevant files it imports\n"
                "2. Determine which approach is correct given the current code state\n"
                "3. Apply the better fix\n"
                "4. Run ruff check and pytest for the affected module\n"
                "5. Create a git commit: fix(<subsystem>): <brief title>"
                + _DOC_UPDATE_STEPS.replace("\n5.", "\n6.").replace("\n6. If", "\n7. If")
            )
        agent = fix["agent_b"] if winning == "b" else fix["agent_a"]
        return (
            f"Fix the following confirmed bug in {fix['file']}:\n\n"
            f"Issue: {fix['title']}\n"
            f"Winning approach: {agent['name']} — {agent['approach']}\n\n"
            f"Proposed diff for reference:\n{agent['diff']}\n\n"
            "Steps:\n"
            f"1. Read {fix['file']} to confirm the exact current code\n"
            "2. Apply the fix described above\n"
            f"3. Run: ruff check {fix['file']}\n"
            "4. If ruff passes, create a git commit: fix(<subsystem>): <brief title>"
            + _DOC_UPDATE_STEPS
        )
    # Dynamic debate
    debate = debates.get(fix_id, {})
    issue_type = debate.get("_issue_type", "unknown issue")
    location = debate.get("_location", "unknown location")
    detail = debate.get("_detail", "see debate")
    location_file = location.split(":")[0]
    winning = debate.get("winning_agent")
    if winning is None:
        a_approach = debate.get("agent_a", {}).get("approach", "see debate")
        b_approach = debate.get("agent_b", {}).get("approach", "see debate")
        return (
            "Fix the following detected code issue (approach undecided — investigate and choose):\n\n"
            f"Location: {location}\nIssue type: {issue_type}\nDetail: {detail}\n\n"
            f"Two approaches proposed:\n- Agent A: {a_approach}\n- Agent B: {b_approach}\n\n"
            f"Steps:\n1. Read {location_file} to confirm the exact current code\n"
            "2. Choose and apply the better fix\n3. Run ruff/pytest as appropriate\n"
            "4. Create a git commit: fix(<subsystem>): <brief description>"
            + _DOC_UPDATE_STEPS
        )
    winner = debate.get("agent_b") if winning == "b" else debate.get("agent_a", {})
    return (
        f"Fix the following detected code issue:\n\n"
        f"Location: {location}\nIssue type: {issue_type}\nDetail: {detail}\n"
        f"Winning approach: {winner.get('name', 'Agent A')} — {winner.get('approach', 'see debate')}\n\n"
        f"Steps:\n1. Read {location_file} to confirm the exact current code\n"
        "2. Apply the fix described above\n3. Run ruff/pytest as appropriate\n"
        "4. Create a git commit: fix(<subsystem>): <brief description>"
        + _DOC_UPDATE_STEPS
    )


def _run_agent_job(fix_id: str, cmd: list) -> None:
    """Worker thread: run claude subprocess and stream output into JOBS[fix_id]."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    with _JOBS_LOCK:
        if fix_id in JOBS:
            JOBS[fix_id]["proc"] = proc
    deadline = time.time() + 300
    for line in proc.stdout:
        with _JOBS_LOCK:
            JOBS[fix_id]["output"].append(line.rstrip())
        if time.time() > deadline:
            proc.kill()
            proc.wait()
            with _JOBS_LOCK:
                JOBS[fix_id]["status"] = "error"
                JOBS[fix_id]["output"].append("[timeout after 300s]")
                JOBS[fix_id]["exit_code"] = -1
            return
    proc.wait()
    with _JOBS_LOCK:
        JOBS[fix_id]["status"] = "done" if proc.returncode == 0 else "error"
        JOBS[fix_id]["exit_code"] = proc.returncode
    if proc.returncode == 0:
        try:
            _mark_fixed(fix_id, _get_latest_commit_sha(), "deploy_agent",
                        f"Deploy agent completed — exit 0")
        except Exception:
            pass  # registry write failure must not crash the worker


# ── HTTP handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence access log

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.send_html(HTML)
        elif self.path == "/api/data":
            open_issues = get_open_issues()
            with _DEBATES_LOCK:
                cached_debates = _load_json_safe(DEBATES_DB) or {}
            result = []
            for item in open_issues:
                fix_id, fix = match_known_fix(item)
                if fix is None and item.get("id") in cached_debates:
                    fix_id = item["id"]
                    fix = dict(cached_debates[item["id"]])
                    # Back-fill missing fields so JS makeBugCard never gets undefined
                    if "title" not in fix:
                        issue0 = item.get("issues", [{}])[0]
                        fix["title"] = issue0.get("type", "issue").replace("-", " ").title()
                    if "explanation" not in fix:
                        fix["explanation"] = item.get("issues", [{}])[0].get("detail", "")
                result.append({**item, "fix_id": fix_id, "known_fix": fix})
            # Enroll new issues into the persistent registry
            _enroll_open_issues(open_issues)
            registry = _load_registry()
            for item in result:
                item["registry"] = registry.get(item.get("id"))
            # Also include fixed issues so the dashboard can show them
            for rid, entry in registry.items():
                if entry.get("status") == "fixed" and not any(r.get("id") == rid for r in result):
                    result.append({
                        "id": rid, "agent": entry.get("agent", ""),
                        "severity": entry.get("severity", ""),
                        "issues": [{"type": entry.get("issue_type", ""),
                                    "location": entry.get("location", ""),
                                    "detail": entry.get("detail", "")}],
                        "fix_id": rid, "known_fix": None,
                        "registry": entry,
                    })
            self.send_json(result)
        elif self.path == "/api/system":
            services = _probe_all_services()
            git = _get_git_status()
            agents = _get_agent_activity()
            resources = _get_system_resources()
            self.send_json({"services": services, "git": git, "agents": agents, "resources": resources})
        elif self.path == "/api/registry":
            self.send_json(_load_registry())
        elif self.path == "/api/jobs":
            with _JOBS_LOCK:
                safe = {k: {kk: vv for kk, vv in v.items() if kk != "proc"}
                        for k, v in JOBS.items()}
            self.send_json(safe)
        elif self.path.startswith("/api/job/"):
            fix_id = self.path.removeprefix("/api/job/")
            with _JOBS_LOCK:
                job = JOBS.get(fix_id)
            if job is None:
                self.send_json({"status": "not_found", "output": [], "exit_code": None}, 404)
            else:
                self.send_json({k: v for k, v in job.items() if k != "proc"})
        # ── Extraction workbench endpoints ──────────────────────────────
        elif self.path == "/api/extraction/fixtures":
            self.send_json(wb_list_fixtures())
        elif self.path == "/api/extraction/tickers":
            self.send_json(wb_list_tickers())
        elif self.path.startswith("/api/extraction/pdfs"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            ticker = qs.get("ticker", [""])[0]
            self.send_json(wb_list_pdfs(ticker))
        elif self.path.startswith("/api/extraction/fixture/"):
            name = self.path.split("/api/extraction/fixture/")[1]
            fixture = wb_load_fixture(name)
            if fixture:
                self.send_json(fixture)
            else:
                self.send_json({"error": "not found"}, 404)
        elif self.path.startswith("/api/extraction/job/"):
            job_id = self.path.split("/api/extraction/job/")[1]
            job = wb_get_job(job_id)
            if job:
                self.send_json(job)
            else:
                self.send_json({"error": "not found"}, 404)
        elif self.path == "/api/extraction/jobs":
            self.send_json(wb_list_jobs())
        elif self.path.startswith("/api/extraction/history/"):
            name = self.path.split("/api/extraction/history/")[1]
            self.send_json(wb_get_history(name))
        elif self.path.startswith("/api/extraction/chat/poll/"):
            cid = self.path.split("/api/extraction/chat/poll/")[1]
            chat = wb_get_chat(cid)
            if chat:
                self.send_json({"ok": True, "status": chat["status"], "messages": chat["messages"]})
            else:
                self.send_json({"ok": False, "error": "Chat not found"}, 404)
        elif self.path == "/api/monitors/status":
            with _SCAN_LOCK:
                self.send_json({
                    "running": _SCAN_STATE["running"],
                    "done": _SCAN_STATE["done"],
                    "status": _SCAN_STATE["status"],
                })
        elif self.path.startswith("/api/chat/poll/"):
            cid = self.path.split("/api/chat/poll/")[1]
            with _DRAWER_LOCK:
                chat = _DRAWER_CHATS.get(cid)
            if chat:
                self.send_json({"ok": True, "status": chat["status"],
                                "messages": [m for m in chat["messages"] if m["role"] != "system"]})
            else:
                self.send_json({"ok": False, "error": "Chat not found"}, 404)
        elif self.path.startswith("/api/pdf/"):
            # Serve PDF files for the viewer
            rel_path = self.path[len("/api/pdf/"):]
            abs_path = WB_FE_ROOT / rel_path
            if abs_path.exists() and abs_path.suffix == ".pdf":
                data = abs_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", len(data))
                self.send_header("Content-Disposition", f"inline; filename={abs_path.name}")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/debate/"):
            issue_id = self.path.split("/api/debate/")[1]
            if not _ISSUE_ID_RE.match(issue_id):
                self.send_json({"ok": False, "message": "Invalid issue_id"}, 400)
                return
            try:
                cl = self.headers.get("Content-Length")
                content_length = int(cl) if cl and cl.strip().isdigit() else 0
                body_bytes = self.rfile.read(min(content_length, 8192))
                body = json.loads(body_bytes.decode("utf-8"))
                issues_list = body.get("issues", [{}])
                issue = issues_list[0] if issues_list else {}
                debate = _generate_debate(
                    issue_id,
                    agent=body.get("agent", ""),
                    severity=body.get("severity", ""),
                    issue_type=issue.get("type", ""),
                    location=issue.get("location", ""),
                    detail=issue.get("detail", ""),
                )
                self.send_json(debate)
            except ValueError as e:
                self.send_json({"ok": False, "message": str(e)}, 400)
            except json.JSONDecodeError as e:
                self.send_json({"ok": False, "message": f"Model response was not valid JSON: {e}"}, 500)
            except Exception as e:
                self.send_json({"ok": False, "message": str(e)}, 500)
            return
        elif self.path.startswith("/api/deploy/"):
            fix_id = self.path.split("/api/deploy/")[1]
            if not (_FIX_ID_SLUG_RE.match(fix_id) or _FIX_ID_SHA1_RE.match(fix_id)):
                self.send_json({"ok": False, "message": "Invalid fix_id"}, 400)
                return
            fix = KNOWN_FIXES.get(fix_id)
            if fix is None:
                with _DEBATES_LOCK:
                    debates = _load_json_safe(DEBATES_DB) or {}
                if fix_id not in debates:
                    self.send_json({"ok": False, "message": f"Unknown fix_id: {fix_id}"}, 404)
                    return
            self.send_json(self._run_deploy(fix_id, fix))
        elif self.path.startswith("/api/job/") and self.path.endswith("/cancel"):
            fix_id = self.path[len("/api/job/"):-len("/cancel")]
            if not (_FIX_ID_SLUG_RE.match(fix_id) or _FIX_ID_SHA1_RE.match(fix_id)):
                self.send_json({"ok": False, "message": "Invalid fix_id"}, 400)
                return
            with _JOBS_LOCK:
                job = JOBS.get(fix_id)
            if job is None:
                self.send_json({"ok": False, "message": "Job not found"}, 404)
                return
            if job["status"] != "running":
                self.send_json({"ok": False, "message": "Job not running"})
                return
            proc = job.get("proc")
            if proc:
                proc.kill()
            with _JOBS_LOCK:
                JOBS[fix_id]["status"] = "cancelled"
                JOBS[fix_id]["output"].append("[cancelled by user]")
            self.send_json({"ok": True})
        elif self.path.startswith("/api/job/") and self.path.endswith("/followup"):
            fix_id = self.path[len("/api/job/"):-len("/followup")]
            if not (_FIX_ID_SLUG_RE.match(fix_id) or _FIX_ID_SHA1_RE.match(fix_id)):
                self.send_json({"ok": False, "message": "Invalid fix_id"}, 400)
                return
            try:
                cl = self.headers.get("Content-Length")
                content_length = int(cl) if cl and cl.strip().isdigit() else 0
                body_bytes = self.rfile.read(min(content_length, 8192))
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                self.send_json({"ok": False, "message": "Bad request body"}, 400)
                return
            question = body.get("question", "").strip()
            if not question:
                self.send_json({"ok": False, "message": "No question provided"}, 400)
                return
            if shutil.which("claude") is None:
                self.send_json({"ok": False, "message": "claude CLI not found"})
                return
            with _JOBS_LOCK:
                parent = JOBS.get(fix_id, {})
            prev_output = "\n".join(parent.get("output", []))[:4000]
            new_id = f"{fix_id[:24]}-q{int(time.time())}"
            prompt = (
                f"Context from previous agent task:\n\n{prev_output}\n\n"
                f"Follow-up question: {question}\n\n"
                "Please answer the follow-up question based on the context above."
            )
            cmd = ["claude", "--print", "-p", prompt]
            with _JOBS_LOCK:
                JOBS[new_id] = {"status": "running", "output": [], "exit_code": None,
                                "proc": None, "title": f"Q: {question[:60]}", "parent": fix_id}
            threading.Thread(target=_run_agent_job, args=(new_id, cmd), daemon=True).start()
            self.send_json({"ok": True, "job_id": new_id})
        elif self.path == "/api/scan-fixes":
            try:
                cl = self.headers.get("Content-Length")
                content_length = int(cl) if cl and cl.strip().isdigit() else 0
                body_bytes = self.rfile.read(min(content_length, 8192))
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                self.send_json({"ok": False, "message": "Bad request body"}, 400)
                return
            commit_sha = body.get("commit_sha", "")
            if not re.match(r'^[a-f0-9]{7,40}$', commit_sha):
                self.send_json({"ok": False, "message": "Invalid commit_sha"}, 400)
                return
            # Get changed files and commit message
            try:
                files_r = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", commit_sha],
                    capture_output=True, text=True, timeout=5, cwd=str(REPO_ROOT))
                changed_files = set(files_r.stdout.strip().splitlines()) if files_r.returncode == 0 else set()
                msg_r = subprocess.run(
                    ["git", "log", "-1", "--format=%s%n%b", commit_sha],
                    capture_output=True, text=True, timeout=5, cwd=str(REPO_ROOT))
                commit_msg = msg_r.stdout.lower() if msg_r.returncode == 0 else ""
            except Exception:
                changed_files, commit_msg = set(), ""
            is_fix_commit = any(w in commit_msg for w in ("fix", "resolve", "patch", "repair"))
            fixed_count, ref_count = 0, 0
            with _REGISTRY_LOCK:
                reg = _load_registry()
                for rid, entry in reg.items():
                    if entry.get("status") != "open":
                        continue
                    loc_file = entry.get("location", "").split(":")[0]
                    if not loc_file:
                        continue
                    file_match = any(loc_file in f or f.endswith(loc_file) for f in changed_files)
                    if file_match and is_fix_commit:
                        entry["status"] = "fixed"
                        entry["fix"] = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "commit_sha": commit_sha,
                            "source": "scan_fixes",
                            "note": f"Auto-detected from commit {commit_sha[:8]}",
                        }
                        fixed_count += 1
                    elif file_match:
                        ref_count += 1
                if fixed_count:
                    _save_registry(reg)
            self.send_json({"ok": True, "scanned": len(reg), "fixed": fixed_count, "referenced": ref_count})
        elif self.path.startswith("/api/bug/") and self.path.endswith("/mark-fixed"):
            issue_id = self.path[len("/api/bug/"):-len("/mark-fixed")]
            if not _FIX_ID_SHA1_RE.match(issue_id):
                self.send_json({"ok": False, "message": "Invalid issue_id"}, 400)
                return
            try:
                cl = self.headers.get("Content-Length")
                content_length = int(cl) if cl and cl.strip().isdigit() else 0
                body_bytes = self.rfile.read(min(content_length, 8192))
                body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except Exception:
                body = {}
            _mark_fixed(
                issue_id,
                commit_sha=body.get("commit_sha", _get_latest_commit_sha()),
                source=body.get("source", "manual"),
                note=body.get("note", "Manually marked as fixed"),
            )
            self.send_json({"ok": True})
        elif self.path == "/api/extraction/run":
            cl = self.headers.get("Content-Length")
            content_length = int(cl) if cl and cl.strip().isdigit() else 0
            body = json.loads(self.rfile.read(min(content_length, 8192)).decode("utf-8"))
            job_id = wb_start_job(
                fixture_name=body.get("fixture_name"),
                pdf_path=body.get("pdf_path"),
                config=body.get("config", {}),
            )
            self.send_json({"ok": True, "job_id": job_id})
        elif self.path.startswith("/api/extraction/cancel/"):
            job_id = self.path.split("/api/extraction/cancel/")[1]
            result = wb_cancel_job(job_id)
            self.send_json(result)
        elif self.path == "/api/extraction/retry":
            cl = self.headers.get("Content-Length")
            content_length = int(cl) if cl and cl.strip().isdigit() else 0
            body = json.loads(self.rfile.read(min(content_length, 8192)).decode("utf-8"))
            job_id = wb_retry_metric(
                pdf_path=body.get("pdf_path", ""),
                metric=body.get("metric", ""),
                config=body.get("config", {}),
            )
            self.send_json({"ok": True, "job_id": job_id})
        elif self.path == "/api/extraction/chat/start":
            cl = self.headers.get("Content-Length")
            content_length = int(cl) if cl and cl.strip().isdigit() else 0
            body = json.loads(self.rfile.read(min(content_length, 8192)).decode("utf-8"))
            self.send_json(wb_start_chat(body.get("job_id", "")))
        elif self.path == "/api/extraction/chat/send":
            cl = self.headers.get("Content-Length")
            content_length = int(cl) if cl and cl.strip().isdigit() else 0
            body = json.loads(self.rfile.read(min(content_length, 8192)).decode("utf-8"))
            self.send_json(wb_send_chat(body.get("chat_id", ""), body.get("message", "")))
        elif self.path == "/api/chat/start":
            cl = self.headers.get("Content-Length")
            content_length = int(cl) if cl and cl.strip().isdigit() else 0
            body = json.loads(self.rfile.read(min(content_length, 5_000_000)).decode("utf-8"))
            # Save screenshot if provided
            screenshot_path = None
            if body.get("screenshot"):
                import base64
                ss_dir = REPO_ROOT / ".claude" / "monitors" / "chat_screenshots"
                ss_dir.mkdir(parents=True, exist_ok=True)
                ss_path = ss_dir / f"ss_{int(time.time())}.png"
                img_data = body["screenshot"].split(",", 1)[-1]  # strip data:image/png;base64,
                ss_path.write_bytes(base64.b64decode(img_data))
                screenshot_path = str(ss_path)
            result = _start_drawer_chat(
                body.get("page_context", ""),
                body.get("message", ""),
                screenshot_path,
            )
            self.send_json(result)
        elif self.path == "/api/chat/send":
            cl = self.headers.get("Content-Length")
            content_length = int(cl) if cl and cl.strip().isdigit() else 0
            body = json.loads(self.rfile.read(min(content_length, 5_000_000)).decode("utf-8"))
            screenshot_path = None
            if body.get("screenshot"):
                import base64
                ss_dir = REPO_ROOT / ".claude" / "monitors" / "chat_screenshots"
                ss_dir.mkdir(parents=True, exist_ok=True)
                ss_path = ss_dir / f"ss_{int(time.time())}.png"
                img_data = body["screenshot"].split(",", 1)[-1]
                ss_path.write_bytes(base64.b64decode(img_data))
                screenshot_path = str(ss_path)
            msg = body.get("message", "")
            if screenshot_path:
                msg = f"[Screenshot saved at {screenshot_path}]\n\n{msg}"
            result = _send_drawer_chat(body.get("chat_id", ""), msg)
            self.send_json(result)
        elif self.path == "/api/monitors/scan":
            with _SCAN_LOCK:
                if _SCAN_STATE["running"]:
                    self.send_json({"ok": False, "error": "Scan already running"})
                    return
            threading.Thread(target=_run_monitor_scan, daemon=True).start()
            self.send_json({"ok": True})
        else:
            self.send_response(404)
            self.end_headers()

    def _run_deploy(self, fix_id: str, fix: dict | None) -> dict:
        if shutil.which("claude") is None:
            return {"ok": False, "message": "claude CLI not found — ensure it is on PATH"}
        with _DEBATES_LOCK:
            debates = _load_json_safe(DEBATES_DB) or {}
        task = _build_task_string(fix_id, fix, debates)
        cmd = ["claude", "--allowedTools", "Edit,Read,Bash,Glob,Grep", "--print", "-p", task]
        title = fix.get("title", fix_id) if fix else fix_id
        with _JOBS_LOCK:
            JOBS[fix_id] = {"status": "running", "output": [], "exit_code": None,
                            "proc": None, "title": title}
        threading.Thread(target=_run_agent_job, args=(fix_id, cmd), daemon=True).start()
        return {"ok": True, "status": "running"}


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    server = ThreadedHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Bug Monitor UI → http://localhost:{PORT}", flush=True)
    print(f"Reading alerts from: {LOG_FILE}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
