from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_override_env(
    path: Path, model_path: Path, extraction_model_path: Path
) -> None:
    path.write_text(
        "\n".join(
            [
                f"LLAMA_SERVER_MODEL={model_path}",
                "LLAMA_SERVER_ALIAS=test-chat-model",
                "LLAMA_SERVER_PORT=8123",
                "LLAMA_SERVER_ROUTER_MODE=0",
                f"EXTRACTION_SERVER_MODEL={extraction_model_path}",
                "EXTRACTION_SERVER_ALIAS=test-extract-model",
                "EXTRACTION_SERVER_PORT=8124",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _base_env(tmp_path: Path, env_file: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env["LLAMA_SERVER_ENV_FILE"] = str(env_file)
    env["LLAMA_SERVER_BIN"] = "/bin/echo"
    env["LOCKFILE"] = str(tmp_path / "launcher.lock")
    env["PYTHON_BIN"] = sys.executable
    env["TENN_EXTRACTION_ACTIVE_FILE"] = str(tmp_path / "gpu-active.json")
    return env


def _write_fake_llama_server(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env bash\n"
        'printf "FAKE_EXECUTABLE=%s\\n" "$0"\n'
        'printf "FAKE_LD_LIBRARY_PATH=%s\\n" "${LD_LIBRARY_PATH:-}"\n'
        'printf "FAKE_ARGS=%s\\n" "$*"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_llama_launcher(
    tmp_path: Path,
    binary: Path,
    *,
    ld_library_path: str | None = None,
) -> subprocess.CompletedProcess[str]:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)
    env = _base_env(tmp_path, env_file)
    env["LLAMA_SERVER_BIN"] = str(binary)
    env["LLAMA_SERVER_ROUTER_MODE"] = "0"
    if ld_library_path is None:
        env.pop("LD_LIBRARY_PATH", None)
    else:
        env["LD_LIBRARY_PATH"] = ld_library_path

    return subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_from_cockpit_launch_context(
    tmp_path: Path,
    binary: Path,
) -> subprocess.CompletedProcess[str]:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)
    env = _base_env(tmp_path, env_file)
    env["LLAMA_SERVER_ROUTER_MODE"] = "0"

    return subprocess.run(
        [
            "bash",
            "-c",
            (
                'set -euo pipefail; '
                'REPO_ROOT="$1"; '
                'source "$REPO_ROOT/scripts/start_config.env"; '
                'export LLAMA_SERVER_BIN="$2"; '
                'exec bash "$REPO_ROOT/scripts/run_llama_server.sh"'
            ),
            "bash",
            str(REPO_ROOT),
            str(binary),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_run_llama_server_loads_host_override_file(tmp_path: Path) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=_base_env(tmp_path, env_file),
        capture_output=True,
        text=True,
        check=True,
    )

    stdout = completed.stdout
    assert f"-m {chat_model}" in stdout
    assert "-a test-chat-model" in stdout
    assert "--port 8123" in stdout


def test_run_llama_server_uses_parallel_override(tmp_path: Path) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)
    env = _base_env(tmp_path, env_file)
    env["LLAMA_SERVER_PARALLEL"] = "2"

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    stdout = completed.stdout
    assert "[llama-server] PARALLEL=2" in stdout
    assert "--parallel 2" in stdout


def test_run_llama_server_preserves_cuda_mask_and_default_mmap(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)
    with env_file.open("a", encoding="utf-8") as handle:
        handle.write("LLAMA_SERVER_CUDA_VISIBLE_DEVICES=0\n")

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=_base_env(tmp_path, env_file),
        capture_output=True,
        text=True,
        check=True,
    )

    stdout = completed.stdout
    assert "[llama-server] CUDA_VISIBLE_DEVICES=0" in stdout
    assert "--no-mmap" not in stdout


def test_run_llama_server_sets_ld_library_path_before_router_probe(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    bin_dir = tmp_path / "llama-bin"
    bin_dir.mkdir()
    fake_bin = bin_dir / "llama-server"
    fake_bin.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'if [[ "${1:-}" == "--help" ]]; then',
                f'  [[ "$0" == "{fake_bin}" ]] || exit 126',
                '  case ":${LD_LIBRARY_PATH:-}:" in',
                f'    *":{bin_dir}:"*) echo "--models-dir PATH"; exit 0 ;;',
                "    *) exit 127 ;;",
                "  esac",
                "fi",
                'printf "%s\\n" "$*"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_bin.chmod(0o755)
    configured_dir = tmp_path / "configured-router-bin"
    configured_dir.mkdir()
    configured_bin = configured_dir / "llama-server"
    configured_bin.symlink_to(fake_bin)
    env_file.write_text(
        "\n".join(
            [
                f"LLAMA_SERVER_MODELS_DIR={models_dir}",
                "LLAMA_SERVER_ROUTER_MODE=1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env = _base_env(tmp_path, env_file)
    env["LLAMA_SERVER_BIN"] = str(configured_bin)
    env["LLAMA_SERVER_PORT"] = "8125"

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    stdout = completed.stdout
    assert "[llama-server] ROUTER_MODE=enabled" in stdout
    assert f"--models-dir {models_dir}" in stdout
    assert "--ctx-size" not in stdout
    assert "--batch-size" not in stdout
    assert "--ubatch-size" not in stdout
    assert "--n-gpu-layers" not in stdout


def test_run_llama_server_uses_resolved_target_for_router_probe(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    target_dir = tmp_path / "router resolved bin"
    target_dir.mkdir()
    target = target_dir / "llama-server"
    target.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'if [[ "${1:-}" == "--help" ]]; then',
                '  printf "%s\\n" "--models-dir PATH"',
                "  exit 0",
                "fi",
                'printf "FAKE_EXECUTABLE=%s\\n" "$0"',
                'printf "FAKE_LD_LIBRARY_PATH=%s\\n" "${LD_LIBRARY_PATH:-}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    target.chmod(0o755)
    link_dir = tmp_path / "router configured bin"
    link_dir.mkdir()
    link = link_dir / "llama-server"
    link.symlink_to(target)

    env = _base_env(tmp_path, env_file)
    env["LLAMA_SERVER_BIN"] = str(link)
    env["LLAMA_SERVER_MODELS_DIR"] = str(models_dir)
    env["LLAMA_SERVER_ROUTER_MODE"] = "1"
    env["LLAMA_SERVER_PORT"] = "8126"
    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "[llama-server] ROUTER_MODE=enabled" in completed.stdout
    assert f"FAKE_EXECUTABLE={target}" in completed.stdout
    assert f"FAKE_EXECUTABLE={link}" not in completed.stdout
    assert f"FAKE_LD_LIBRARY_PATH={target_dir}" in completed.stdout


def test_run_llama_server_fails_closed_when_router_capability_is_missing(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    fake_bin = tmp_path / "llama-server"
    fake_bin.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'if [[ "${1:-}" == "--help" ]]; then',
                '  echo "--model PATH"',
                "  exit 0",
                "fi",
                'echo "FAKE_SERVER_STARTED"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_bin.chmod(0o755)
    env_file.write_text(
        "\n".join(
            [
                f"LLAMA_SERVER_MODELS_DIR={models_dir}",
                "LLAMA_SERVER_ROUTER_MODE=1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    env = _base_env(tmp_path, env_file)
    env["LLAMA_SERVER_BIN"] = str(fake_bin)
    env["LLAMA_SERVER_PORT"] = "8125"

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "router mode was requested" in completed.stderr
    assert "FAKE_SERVER_STARTED" not in completed.stdout
    assert "ROUTER_MODE=disabled" not in completed.stdout


def test_run_llama_server_uses_resolved_symlink_target_for_library_path(
    tmp_path: Path,
) -> None:
    target_dir = tmp_path / "resolved bin"
    target_dir.mkdir()
    target = target_dir / "llama-server"
    _write_fake_llama_server(target)
    link_dir = tmp_path / "configured bin"
    link_dir.mkdir()
    link = link_dir / "llama-server"
    link.symlink_to(target)

    completed = _run_llama_launcher(tmp_path, link)

    assert completed.returncode == 0, completed.stderr
    assert f"FAKE_EXECUTABLE={target}" in completed.stdout
    assert f"FAKE_LD_LIBRARY_PATH={target_dir}" in completed.stdout


def test_cockpit_launch_context_renders_resolved_serving_path(
    tmp_path: Path,
) -> None:
    target_dir = tmp_path / "cockpit resolved bin"
    target_dir.mkdir()
    target = target_dir / "llama-server"
    _write_fake_llama_server(target)
    link_dir = tmp_path / "cockpit configured bin"
    link_dir.mkdir()
    link = link_dir / "llama-server"
    link.symlink_to(target)

    completed = _run_from_cockpit_launch_context(tmp_path, link)

    assert completed.returncode == 0, completed.stderr
    assert f"FAKE_EXECUTABLE={target}" in completed.stdout
    assert f"FAKE_EXECUTABLE={link}" not in completed.stdout
    assert f"FAKE_LD_LIBRARY_PATH={target_dir}" in completed.stdout


def test_run_llama_server_uses_direct_executable_directory_for_library_path(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "direct-bin"
    bin_dir.mkdir()
    binary = bin_dir / "llama-server"
    _write_fake_llama_server(binary)

    completed = _run_llama_launcher(tmp_path, binary)

    assert completed.returncode == 0, completed.stderr
    assert f"FAKE_EXECUTABLE={binary}" in completed.stdout
    assert f"FAKE_LD_LIBRARY_PATH={bin_dir}" in completed.stdout


def test_run_llama_server_prepends_library_dir_to_existing_path(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "direct-bin"
    bin_dir.mkdir()
    binary = bin_dir / "llama-server"
    _write_fake_llama_server(binary)
    existing_path = "/existing/first:/existing/second"

    completed = _run_llama_launcher(
        tmp_path,
        binary,
        ld_library_path=existing_path,
    )

    assert completed.returncode == 0, completed.stderr
    assert f"FAKE_LD_LIBRARY_PATH={bin_dir}:{existing_path}" in completed.stdout


def test_run_llama_server_fails_closed_for_broken_configured_target(
    tmp_path: Path,
) -> None:
    broken_link = tmp_path / "broken-bin" / "llama-server"
    broken_link.parent.mkdir()
    broken_link.symlink_to(tmp_path / "missing" / "llama-server")

    completed = _run_llama_launcher(tmp_path, broken_link)

    assert completed.returncode == 1
    assert (
        f"Unable to resolve llama-server binary target at {broken_link}"
        in completed.stderr
    )
    assert "Starting llama-server" not in completed.stdout


def test_run_llama_server_fails_closed_for_missing_configured_target(
    tmp_path: Path,
) -> None:
    missing_binary = tmp_path / "missing bin" / "llama-server"

    completed = _run_llama_launcher(tmp_path, missing_binary)

    assert completed.returncode == 1
    assert (
        f"Unable to resolve llama-server binary target at {missing_binary}"
        in completed.stderr
    )
    assert "Starting llama-server" not in completed.stdout


def test_run_llama_server_fails_closed_for_non_executable_target(
    tmp_path: Path,
) -> None:
    binary = tmp_path / "not executable" / "llama-server"
    binary.parent.mkdir()
    binary.write_text(
        "#!/usr/bin/env bash\nprintf 'unexpected launch\\n'\n",
        encoding="utf-8",
    )
    binary.chmod(0o644)

    completed = _run_llama_launcher(tmp_path, binary)

    assert completed.returncode == 1
    assert f"binary target is not executable at {binary}" in completed.stderr
    assert "unexpected launch" not in completed.stdout


def test_run_llama_server_refuses_during_gpu_exclusive_activity(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)

    active_file = tmp_path / "gpu-active.json"
    active_file.write_text(
        json.dumps(
            {
                "tokens": {"manual-token": time.time() + 600},
                "metadata": {
                    "manual-token": {
                        "activity_type": "gpu_exclusive",
                        "reason": "test",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=_base_env(tmp_path, env_file),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 75
    assert "GPU-exclusive activity active" in completed.stderr


def test_run_extraction_server_loads_host_override_file(tmp_path: Path) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_extraction_server.sh")],
        cwd=REPO_ROOT,
        env=_base_env(tmp_path, env_file),
        capture_output=True,
        text=True,
        check=True,
    )

    stdout = completed.stdout
    assert f"-m {extraction_model}" in stdout
    assert "-a test-extract-model" in stdout
    assert "--port 8124" in stdout
