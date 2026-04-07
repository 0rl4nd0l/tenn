from __future__ import annotations

import os
import subprocess
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
    env["LLAMA_SERVER_ROUTER_MODE"] = "0"
    return env


def _write_fake_llama_server(path: Path, *, help_output: str) -> None:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'if [[ "${1:-}" == "--help" ]]; then',
                f'  echo "{help_output}"',
                "  exit 0",
                "fi",
                'echo "$@"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


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


def test_run_llama_server_uses_hf_flag_when_binary_supports_it(tmp_path: Path) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)

    fake_bin = tmp_path / "fake-llama-server"
    _write_fake_llama_server(fake_bin, help_output="--hf --models-dir")
    env = _base_env(tmp_path, env_file)
    env["LLAMA_SERVER_BIN"] = str(fake_bin)
    env["LLAMA_SERVER_ROUTER_MODE"] = "0"
    env["LLAMA_SERVER_HF_REPO"] = "acme/test-gguf"

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    stdout = completed.stdout
    assert "--hf acme/test-gguf" in stdout
    assert f"-m {chat_model}" not in stdout


def test_run_llama_server_falls_back_to_local_model_when_hf_unsupported(tmp_path: Path) -> None:
    config_dir = tmp_path / ".config" / "tenn"
    config_dir.mkdir(parents=True)
    env_file = config_dir / "llama-server.env"
    chat_model = tmp_path / "chat-model.gguf"
    extraction_model = tmp_path / "extract-model.gguf"
    chat_model.write_text("chat", encoding="utf-8")
    extraction_model.write_text("extract", encoding="utf-8")
    _write_override_env(env_file, chat_model, extraction_model)

    fake_bin = tmp_path / "fake-llama-server"
    _write_fake_llama_server(fake_bin, help_output="--model --port")
    env = _base_env(tmp_path, env_file)
    env["LLAMA_SERVER_BIN"] = str(fake_bin)
    env["LLAMA_SERVER_ROUTER_MODE"] = "0"
    env["LLAMA_SERVER_HF_REPO"] = "acme/test-gguf"

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "run_llama_server.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    stdout = completed.stdout
    stderr = completed.stderr
    assert f"-m {chat_model}" in stdout
    assert "--hf acme/test-gguf" not in stdout
    assert "--hf is not supported" in stderr
