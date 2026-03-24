"""Restart the financial-engine backend uvicorn process."""
from __future__ import annotations

import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

_HEALTH_URL = "http://127.0.0.1:8000/api/health"
_RESTART_TIMEOUT_S = 30


def restart_backend(repo_root: Path) -> None:
    """Kill the running uvicorn backend and relaunch it via run_local_backend.sh."""
    script = repo_root / "scripts" / "run_local_backend.sh"

    # 1. Locate the running backend process.
    pgrep = subprocess.run(
        ["pgrep", "-f", "uvicorn app.main:app"],
        capture_output=True,
        text=True,
    )
    pids = pgrep.stdout.strip().split()

    if pids:
        pid_str = pids[0]
        print(f"Stopping backend (PID {pid_str})…", flush=True)
        kill = subprocess.run(["kill", pid_str], capture_output=True)
        if kill.returncode != 0:
            # Backend may be owned by root — escalate.
            subprocess.run(["sudo", "kill", pid_str], check=True)
        # Wait for the process to exit (read /proc — no privilege needed).
        deadline = time.time() + 10
        while Path(f"/proc/{pid_str}").exists() and time.time() < deadline:
            time.sleep(0.3)
    else:
        print("No running backend found — starting fresh.", flush=True)

    # 2. Relaunch in a detached process so this call returns promptly.
    profile = os.getenv("LOCAL_BACKEND_PROFILE", "isolated")
    env = os.environ.copy()
    env["LOCAL_BACKEND_PROFILE"] = profile
    print(f"Starting backend (profile={profile})…", flush=True)
    subprocess.Popen(
        ["bash", str(script)],
        env=env,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 3. Poll health until up or timeout.
    print(f"Waiting for {_HEALTH_URL}…", flush=True)
    deadline = time.time() + _RESTART_TIMEOUT_S
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(_HEALTH_URL, timeout=2) as resp:
                if resp.status == 200:
                    print("Backend is up.", flush=True)
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    print(
        f"WARNING: backend did not respond within {_RESTART_TIMEOUT_S}s — "
        "check logs.",
        flush=True,
    )
