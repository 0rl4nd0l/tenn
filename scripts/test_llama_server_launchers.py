from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_override_env(path: Path, model_path: Path, extraction_model_path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                f"LLAMA_SERVER_MODEL={model_path}",
                "LLAMA_SERVER_ALIAS=test-chat-model",
                "LLAMA_SERVER_PORT=8123",
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
        check=True,
    )

    stdout = completed.stdout
    assert "[llama-server] ROUTER_MODE=enabled" in stdout
    assert f"--models-dir {models_dir}" in stdout


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
