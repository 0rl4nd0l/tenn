#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCLING_VENV = REPO_ROOT / ".venv_docling"
LEGACY_DOCLING_VENVS = (
    REPO_ROOT / ".venv-docling-gpu",
    REPO_ROOT / ".venv-docling-gpu-repair",
)


@dataclass(frozen=True)
class DoclingRuntimeState:
    venv_path: str
    python_path: str
    exists: bool
    created: bool
    import_ok: bool
    legacy_candidate: str | None
    error: str


def _resolve_path(value: str | Path | None) -> Path:
    path = Path(value or DEFAULT_DOCLING_VENV).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _resolve_cwd(value: str | Path | None) -> Path:
    path = Path(value or REPO_ROOT).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _python_path(venv_path: Path) -> Path:
    return venv_path / "bin" / "python"


def _legacy_candidate() -> Path | None:
    for candidate in LEGACY_DOCLING_VENVS:
        if _python_path(candidate).exists():
            return candidate
    return None


def ensure_docling_venv(
    *,
    venv_path: str | Path | None = None,
    create_if_missing: bool = False,
) -> DoclingRuntimeState:
    resolved_venv = _resolve_path(venv_path)
    python_bin = _python_path(resolved_venv)
    created = False
    error = ""

    if not python_bin.exists() and create_if_missing:
        resolved_venv.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, "-m", "venv", str(resolved_venv)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        created = True
        python_bin = _python_path(resolved_venv)

    legacy = _legacy_candidate()
    import_ok = False
    if python_bin.exists():
        probe = subprocess.run(
            [str(python_bin), "-c", "import docling"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        import_ok = probe.returncode == 0
        if not import_ok:
            error = probe.stderr.strip() or probe.stdout.strip() or "docling_import_failed"
    else:
        error = "docling_venv_missing"

    return DoclingRuntimeState(
        venv_path=str(resolved_venv),
        python_path=str(python_bin),
        exists=python_bin.exists(),
        created=created,
        import_ok=import_ok,
        legacy_candidate=str(legacy) if legacy is not None else None,
        error=error,
    )


def build_docling_env(
    *,
    python_path: str | Path,
    extra_env: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    python_bin = Path(str(python_path)).resolve()
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["VIRTUAL_ENV"] = str(python_bin.parent.parent)
    current_path = str(env.get("PATH", "")).strip()
    env["PATH"] = str(python_bin.parent) if not current_path else f"{python_bin.parent}:{current_path}"
    for key, value in dict(extra_env or {}).items():
        env[str(key)] = str(value)
    return env


def run_docling_subprocess(
    args: Sequence[str],
    *,
    cwd: str | Path | None = None,
    timeout_sec: float | None = None,
    venv_path: str | Path | None = None,
    create_venv_if_missing: bool = False,
    extra_env: Mapping[str, Any] | None = None,
    check: bool = False,
) -> dict[str, Any]:
    state = ensure_docling_venv(
        venv_path=venv_path,
        create_if_missing=create_venv_if_missing,
    )
    if not state.exists:
        return {
            "ok": False,
            "state": asdict(state),
            "command": [],
            "returncode": None,
            "stdout": "",
            "stderr": state.error,
        }
    if not state.import_ok:
        return {
            "ok": False,
            "state": asdict(state),
            "command": [],
            "returncode": None,
            "stdout": "",
            "stderr": state.error,
        }

    command = [state.python_path, *[str(part) for part in args]]
    completed = subprocess.run(
        command,
        cwd=str(_resolve_cwd(cwd)),
        env=build_docling_env(python_path=state.python_path, extra_env=extra_env),
        timeout=timeout_sec,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            command,
            output=completed.stdout,
            stderr=completed.stderr,
        )
    return {
        "ok": completed.returncode == 0,
        "state": asdict(state),
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Docling commands in an isolated venv.")
    parser.add_argument(
        "--venv",
        default=str(DEFAULT_DOCLING_VENV),
        help="Docling virtual environment path. Defaults to .venv_docling at repo root.",
    )
    parser.add_argument(
        "--create-venv",
        action="store_true",
        help="Create the Docling venv if it does not exist.",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Print runtime state JSON and exit.",
    )
    parser.add_argument(
        "--cwd",
        default=str(REPO_ROOT),
        help="Working directory for executed commands.",
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=0.0,
        help="Optional subprocess timeout in seconds.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute inside the Docling venv, prefixed with '--'.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    state = ensure_docling_venv(
        venv_path=args.venv,
        create_if_missing=bool(args.create_venv),
    )
    if args.probe:
        print(json.dumps(asdict(state), indent=2))
        return 0 if state.exists and state.import_ok else 1

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print(json.dumps(asdict(state), indent=2))
        return 0 if state.exists and state.import_ok else 1

    result = run_docling_subprocess(
        command,
        cwd=args.cwd,
        timeout_sec=float(args.timeout_sec or 0.0) or None,
        venv_path=args.venv,
        create_venv_if_missing=bool(args.create_venv),
    )
    if result.get("stdout"):
        print(str(result["stdout"]), end="")
    if result.get("stderr"):
        print(str(result["stderr"]), end="", file=sys.stderr)
    return int(result.get("returncode") or 0) if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
