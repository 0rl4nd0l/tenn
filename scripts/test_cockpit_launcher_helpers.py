from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COCKPIT_SCRIPT = REPO_ROOT / "scripts" / "cockpit"


def _helper_block() -> str:
    script = COCKPIT_SCRIPT.read_text(encoding="utf-8")
    start = script.index("http_ok() {")
    end = script.index("ensure_llama_servers_up() {")
    return script[start:end]


def test_http_ok_adds_bearer_header_when_api_key_is_provided(tmp_path: Path) -> None:
    curl_path = tmp_path / "curl"
    curl_path.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n" "$@" > "$TMPDIR_OUT/args.txt"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    curl_path.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    env["TMPDIR_OUT"] = str(tmp_path)

    completed = subprocess.run(
        [
            "bash",
            "-lc",
            "source /dev/stdin <<'EOF'\n"
            f"{_helper_block()}\n"
            "EOF\n"
            'http_ok "http://127.0.0.1:8001/health" 3 "token-123"\n',
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout == ""
    args = (tmp_path / "args.txt").read_text(encoding="utf-8")
    assert "-H\nAuthorization: Bearer token-123\n" in args
    assert "http://127.0.0.1:8001/health\n" in args


def test_wait_for_health_reports_log_path_on_timeout(tmp_path: Path) -> None:
    curl_path = tmp_path / "curl"
    curl_path.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    curl_path.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"

    completed = subprocess.run(
        [
            "bash",
            "-lc",
            "source /dev/stdin <<'EOF'\n"
            f"{_helper_block()}\n"
            "EOF\n"
            'wait_for_health "llama.cpp chat" "http://127.0.0.1:8001/health" 0 "/tmp/llama-server-8001.log" "token-123"\n',
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "did not become healthy within 0s" in completed.stderr
    assert "See log: /tmp/llama-server-8001.log" in completed.stderr
