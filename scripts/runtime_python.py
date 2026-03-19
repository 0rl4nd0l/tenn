#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCLING_PYTHON_ENV_VARS = ("DOCILING_PYTHON", "DOCLING_PYTHON")


def _fallback_python_path() -> Path:
    return ROOT / ".venv-docling-gpu" / "bin" / "python"


def resolve_python() -> str:
    for env_var in DOCLING_PYTHON_ENV_VARS:
        value = str(os.environ.get(env_var, "")).strip()
        if value:
            return value
    fallback = _fallback_python_path()
    if fallback.exists():
        return str(fallback)
    return "python3"


def print_runtime_info() -> str:
    python_exec = resolve_python()
    print(f"[runtime] using python interpreter: {python_exec}")
    return python_exec


if __name__ == "__main__":
    print_runtime_info()
