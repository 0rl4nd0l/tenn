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


def _process_control_block() -> str:
    script = COCKPIT_SCRIPT.read_text(encoding="utf-8")
    start = script.index("kill_with_fallback() {")
    end = script.index("launch_cockpit_tui() {")
    return script[start:end]


def test_http_ok_adds_bearer_header_when_api_key_is_provided(tmp_path: Path) -> None:
    curl_path = tmp_path / "curl"
    curl_path.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$TMPDIR_OUT/args.txt"\nexit 0\n',
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


def test_ensure_llama_servers_skips_startup_when_gpu_exclusive_active(
    tmp_path: Path,
) -> None:
    calls_file = tmp_path / "calls.txt"

    completed = subprocess.run(
        [
            "bash",
            "-lc",
            "source /dev/stdin <<'EOF'\n"
            f"{_process_control_block()}\n"
            "EOF\n"
            f'REPO_ROOT="{REPO_ROOT}"\n'
            f'ENGINE_ROOT="{tmp_path}"\n'
            f'CALLS_FILE="{calls_file}"\n'
            'gpu_exclusive_activity_active() { return 0; }\n'
            'llama_chat_base_url() { printf "http://127.0.0.1:8001\\n"; }\n'
            'llama_extraction_base_url() { printf "http://127.0.0.1:8002\\n"; }\n'
            'llama_api_key() { printf "token\\n"; }\n'
            'llama_log_path() { printf "/tmp/llama-server-%s.log\\n" "$1"; }\n'
            'http_ok() { printf "http_ok\\n" >> "$CALLS_FILE"; return 1; }\n'
            'wait_for_health() { printf "wait_for_health\\n" >> "$CALLS_FILE"; }\n'
            "ensure_llama_servers_up\n",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "GPU-exclusive activity active; skipping llama.cpp startup" in completed.stdout
    assert calls_file.exists() is False


def test_llama_chat_base_url_prefers_host_endpoint_over_container_env(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env["LLAMACPP_URL"] = "http://172.18.0.1:8001/v1"
    env["LLAMACPP_URL_HOST"] = "http://127.0.0.1:8001/v1"
    env.pop("COCKPIT_LLAMACPP_URL", None)

    completed = subprocess.run(
        [
            "bash",
            "-lc",
            f"source /dev/stdin <<'EOF'\n{_helper_block()}\nEOF\nllama_chat_base_url\n",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout.strip() == "http://127.0.0.1:8001"


def test_launch_cockpit_new_defaults_to_web_port_8081() -> None:
    script = COCKPIT_SCRIPT.read_text(encoding="utf-8")

    assert 'local port="${COCKPIT_NEW_PORT:-${COCKPIT_WEB_PORT:-8081}}"' in script


def test_usage_lists_reboot_command() -> None:
    script = COCKPIT_SCRIPT.read_text(encoding="utf-8")

    assert "cockpit reboot" in script


def test_usage_lists_routing_smoke_command() -> None:
    script = COCKPIT_SCRIPT.read_text(encoding="utf-8")

    assert "cockpit smoke routing" in script
    assert "cockpit_routing_smoke.py" in script


def test_start_config_defaults_marketplace_to_direct_runtime() -> None:
    config = (REPO_ROOT / "scripts" / "start_config.env").read_text(encoding="utf-8")

    assert 'COCKPIT_STATE_DB_ON_STARTUP="/mnt/tenn-nvme2/tenn/financial-engine_v2/data/cockpit/state.db"' in config
    assert 'MARKETPLACE_BROWSER_RUNTIME_ON_STARTUP="direct"' in config
    assert 'MARKETPLACE_BROWSER_PROFILE_DIR_ON_STARTUP="/root/.tenn/browser_profiles/facebook-marketplace-chrome"' in config


def test_start_full_stack_propagates_marketplace_runtime_flags() -> None:
    script = (REPO_ROOT / "scripts" / "start_full_stack.sh").read_text(encoding="utf-8")

    assert 'set_env_key "COCKPIT_STATE_DB"' in script
    assert 'export COCKPIT_STATE_DB="${COCKPIT_STATE_DB_ON_STARTUP}"' in script
    assert 'set_env_key "MARKETPLACE_BROWSER_RUNTIME"' in script
    assert 'set_env_key "MARKETPLACE_BROWSER_PROFILE_DIR"' in script
    assert 'export MARKETPLACE_BROWSER_RUNTIME="${MARKETPLACE_BROWSER_RUNTIME_ON_STARTUP}"' in script


def test_start_full_stack_exports_backend_git_provenance_env() -> None:
    script = (REPO_ROOT / "scripts" / "start_full_stack.sh").read_text(encoding="utf-8")

    assert "export_git_provenance_env()" in script
    assert "git -C \"${REPO_ROOT}\" rev-parse HEAD" in script
    assert 'export TENN_GIT_HEAD="${TENN_GIT_HEAD:-${head}}"' in script
    assert 'export TENN_GIT_BRANCH="${TENN_GIT_BRANCH:-${branch}}"' in script
    assert 'export TENN_GIT_STATUS_LINE_COUNT="${TENN_GIT_STATUS_LINE_COUNT:-${status_line_count}}"' in script


def test_stop_backend_api_falls_back_to_sudo_for_root_owned_process(
    tmp_path: Path,
) -> None:
    engine_root = tmp_path / "financial-engine_v2"
    engine_root.mkdir()
    sudo_args = tmp_path / "sudo_args.txt"

    completed = subprocess.run(
        [
            "bash",
            "-lc",
            "source /dev/stdin <<'EOF'\n"
            f"{_process_control_block()}\n"
            "EOF\n"
            f'ENGINE_ROOT="{engine_root}"\n'
            "COMPOSE=(false)\n"
            f'SUDO_ARGS_FILE="{sudo_args}"\n'
            "pgrep() {\n"
            '  if [[ "$*" == *"uvicorn app.main:app"* ]]; then printf "2026153\\n"; fi\n'
            "}\n"
            "kill() { return 1; }\n"
            'sudo() { printf "%s\\n" "$*" >> "$SUDO_ARGS_FILE"; return 0; }\n'
            "stop_backend_api\n",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Stopping local backend API process (PID 2026153)" in completed.stdout
    assert sudo_args.read_text(encoding="utf-8").strip() == "kill 2026153"


def test_cockpit_kill_root_uses_sudo_fallback_for_listener_cleanup(
    tmp_path: Path,
) -> None:
    ss_path = tmp_path / "ss"
    ss_path.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "$*" == *":8081"* ]]; then\n'
        '  printf "LISTEN 0 2048 0.0.0.0:8081 0.0.0.0:* users:((\\"next-server\\",pid=4242,fd=24))\\n"\n'
        "fi\n",
        encoding="utf-8",
    )
    ss_path.chmod(0o755)

    sudo_args = tmp_path / "sudo_args.txt"
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"

    completed = subprocess.run(
        [
            "bash",
            "-lc",
            "source /dev/stdin <<'EOF'\n"
            f"{_process_control_block()}\n"
            "EOF\n"
            f'ENGINE_ROOT="{tmp_path}"\n'
            f'REPO_ROOT="{REPO_ROOT}"\n'
            "COCKPIT_WEB_PORT=8081\n"
            "COCKPIT_NEW_PORT=8081\n"
            f'SUDO_ARGS_FILE="{sudo_args}"\n'
            "pgrep() { return 0; }\n"
            "kill() { return 1; }\n"
            'sudo() { printf "%s\\n" "$*" >> "$SUDO_ARGS_FILE"; return 0; }\n'
            "cockpit_kill_root\n",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Freeing Cockpit UI port 8081 (PIDs: 4242)" in completed.stdout
    assert "Done." in completed.stdout
    assert "kill 4242" in sudo_args.read_text(encoding="utf-8")


def test_reboot_cockpit_runs_shutdown_then_start_sequence(tmp_path: Path) -> None:
    calls_file = tmp_path / "calls.txt"

    completed = subprocess.run(
        [
            "bash",
            "-lc",
            "source /dev/stdin <<'EOF'\n"
            f"{_process_control_block()}\n"
            "EOF\n"
            f'REPO_ROOT="{REPO_ROOT}"\n'
            f'CALLS_FILE="{calls_file}"\n'
            'stop_backend_api() { printf "stop_backend_api\\n" >> "$CALLS_FILE"; }\n'
            'stop_llama_servers() { printf "stop_llama_servers\\n" >> "$CALLS_FILE"; }\n'
            'cockpit_kill_root() { printf "cockpit_kill_root\\n" >> "$CALLS_FILE"; }\n'
            'start_full_stack() { printf "start_full_stack\\n" >> "$CALLS_FILE"; }\n'
            'start_all_backends_safely() { printf "start_all_backends_safely\\n" >> "$CALLS_FILE"; }\n'
            'backend_health_url() { printf "http://127.0.0.1:8000/api/health\\n"; }\n'
            'wait_for_health() { printf "wait_for_health %s %s %s\\n" "$1" "$2" "$3" >> "$CALLS_FILE"; }\n'
            'launch_cockpit_new() { printf "launch_cockpit_new\\n" >> "$CALLS_FILE"; }\n'
            "reboot_cockpit\n",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout == ""
    assert calls_file.read_text(encoding="utf-8").splitlines() == [
        "stop_backend_api",
        "stop_llama_servers",
        "cockpit_kill_root",
        "start_full_stack",
        "start_all_backends_safely",
        "wait_for_health Backend API http://127.0.0.1:8000/api/health 120",
        "launch_cockpit_new",
    ]
