#!/usr/bin/env python3
"""Run pytest with a safe fallback when the selected runtime venv lacks pytest.

This helper exists for fresh Tenn worktrees where product/runtime dependencies
are available in a repo venv, but pytest was not installed in that venv. It
never installs into the runtime venv. If pytest is missing, it creates a
throwaway overlay venv under /tmp, installs validation-only pytest packages
there, and exposes the base venv site-packages through PYTHONPATH.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
DEFAULT_BASE_PYTHONS = (
    REPO_ROOT / "financial-engine_v2" / ".venv" / "bin" / "python",
    REPO_ROOT / ".venv" / "bin" / "python",
)
DEFAULT_OVERLAY_PACKAGES = (
    "pytest>=8.3.3,<10",
    "pytest-asyncio>=0.24.0,<2",
    "respx>=0.23.1,<0.24",
)
DEFAULT_PYTHONPATH = (
    REPO_ROOT,
    REPO_ROOT / "financial-engine_v2",
    BACKEND_ROOT,
    REPO_ROOT / "scripts",
)


@dataclass(frozen=True)
class PytestPlan:
    mode: str
    base_python: str
    runner_python: str
    pytest_command: list[str]
    install_command: list[str]
    overlay_dir: str | None
    target_site_packages: list[str]
    pythonpath: list[str]


def normalize_pytest_args(args: Sequence[str]) -> list[str]:
    normalized = list(args)
    if normalized and normalized[0] == "--":
        normalized = normalized[1:]
    has_config = any(arg == "-c" or arg.startswith("-c") for arg in normalized)
    if not has_config:
        normalized = ["-c", "pytest.ini", *normalized]
    return normalized


def candidate_base_pythons(explicit: str | None, env: dict[str, str] | None = None) -> list[Path]:
    env = env or os.environ
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_python = env.get("TENN_PYTEST_BASE_PYTHON")
    if env_python:
        candidates.append(Path(env_python).expanduser())
    candidates.extend(DEFAULT_BASE_PYTHONS)
    candidates.append(Path(sys.executable))

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        resolved = str(candidate)
        if resolved not in seen:
            seen.add(resolved)
            unique.append(candidate)
    return unique


def choose_base_python(explicit: str | None, env: dict[str, str] | None = None) -> Path:
    if explicit:
        explicit_path = Path(os.path.abspath(Path(explicit).expanduser()))
        if not explicit_path.exists() or not os.access(explicit_path, os.X_OK):
            raise RuntimeError(f"explicit base Python is not executable: {explicit_path}")
        return explicit_path
    for candidate in candidate_base_pythons(explicit, env):
        if candidate.exists() and os.access(candidate, os.X_OK):
            return Path(os.path.abspath(candidate))
    raise RuntimeError("no executable Python found for pytest fallback")


def python_has_module(python: Path, module: str) -> bool:
    proc = subprocess.run(
        [str(python), "-c", f"import {module}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.returncode == 0


def python_site_packages(python: Path) -> list[str]:
    script = (
        "import json, sysconfig; "
        "paths=sysconfig.get_paths(); "
        "print(json.dumps([paths.get('purelib'), paths.get('platlib')]))"
    )
    proc = subprocess.run(
        [str(python), "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    loaded = json.loads(proc.stdout)
    paths: list[str] = []
    for item in loaded:
        if item and item not in paths:
            paths.append(str(item))
    return paths


def merged_pythonpath(paths: Sequence[str | Path], existing: str | None = None) -> str:
    merged: list[str] = []
    for path in paths:
        text = str(path)
        if text and text not in merged:
            merged.append(text)
    if existing:
        for text in existing.split(os.pathsep):
            if text and text not in merged:
                merged.append(text)
    return os.pathsep.join(merged)


def create_overlay(base_python: Path, *, packages: Sequence[str]) -> tuple[Path, list[str]]:
    overlay_dir = Path(tempfile.mkdtemp(prefix="tenn-pytest-overlay-", dir="/tmp")).resolve()
    try:
        subprocess.run([str(base_python), "-m", "venv", str(overlay_dir)], check=True)
        runner_python = overlay_dir / "bin" / "python"
        install_command = [
            str(runner_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            *packages,
        ]
        subprocess.run(install_command, check=True)
        return overlay_dir, install_command
    except Exception:
        shutil.rmtree(overlay_dir, ignore_errors=True)
        raise


def build_plan(
    *,
    base_python: Path,
    pytest_args: Sequence[str],
    pytest_available: bool,
    target_site_packages: Sequence[str],
    overlay_dir: Path | None = None,
    overlay_packages: Sequence[str] = DEFAULT_OVERLAY_PACKAGES,
    existing_pythonpath: str | None = None,
) -> PytestPlan:
    pythonpath = [
        *[str(path) for path in DEFAULT_PYTHONPATH],
        *[str(path) for path in target_site_packages],
    ]
    env_pythonpath = merged_pythonpath(pythonpath, existing_pythonpath)
    normalized_args = normalize_pytest_args(pytest_args)

    if pytest_available:
        runner_python = base_python
        mode = "direct"
        install_command: list[str] = []
        overlay_text = None
    else:
        overlay_dir = overlay_dir or Path("/tmp/tenn-pytest-overlay-DRY-RUN")
        runner_python = overlay_dir / "bin" / "python"
        mode = "ephemeral_overlay"
        install_command = [
            str(runner_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            *overlay_packages,
        ]
        overlay_text = str(overlay_dir)

    return PytestPlan(
        mode=mode,
        base_python=str(base_python),
        runner_python=str(runner_python),
        pytest_command=[str(runner_python), "-m", "pytest", *normalized_args],
        install_command=install_command,
        overlay_dir=overlay_text,
        target_site_packages=list(target_site_packages),
        pythonpath=env_pythonpath.split(os.pathsep) if env_pythonpath else [],
    )


def write_report(path: Path | None, payload: dict[str, object]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-python", default="", help="Preferred runtime/dependency Python.")
    parser.add_argument("--report-json", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved plan without running pytest.")
    parser.add_argument(
        "--keep-overlay",
        action="store_true",
        help="Do not delete the ephemeral overlay venv after the pytest run.",
    )
    parser.add_argument(
        "--overlay-package",
        action="append",
        default=[],
        help="Validation-only package to install in the overlay when pytest is missing.",
    )
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    base_python = choose_base_python(args.base_python or None)
    target_site_packages = python_site_packages(base_python)
    pytest_available = python_has_module(base_python, "pytest")
    packages = tuple(args.overlay_package or DEFAULT_OVERLAY_PACKAGES)
    overlay_dir: Path | None = None
    install_command: list[str] = []

    try:
        if not pytest_available and not args.dry_run:
            overlay_dir, install_command = create_overlay(base_python, packages=packages)

        plan = build_plan(
            base_python=base_python,
            pytest_args=args.pytest_args,
            pytest_available=pytest_available,
            target_site_packages=target_site_packages,
            overlay_dir=overlay_dir,
            overlay_packages=packages,
            existing_pythonpath=os.environ.get("PYTHONPATH"),
        )
        if install_command:
            plan = PytestPlan(
                mode=plan.mode,
                base_python=plan.base_python,
                runner_python=plan.runner_python,
                pytest_command=plan.pytest_command,
                install_command=install_command,
                overlay_dir=plan.overlay_dir,
                target_site_packages=plan.target_site_packages,
                pythonpath=plan.pythonpath,
            )

        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(plan.pythonpath)
        report: dict[str, object] = {"status": "DRY_RUN" if args.dry_run else "RUNNING", "plan": asdict(plan)}

        if args.dry_run:
            print(json.dumps(report, indent=2, sort_keys=True))
            write_report(args.report_json, report)
            return 0

        proc = subprocess.run(plan.pytest_command, env=env, check=False)
        report["status"] = "PASS" if proc.returncode == 0 else "FAIL"
        report["returncode"] = proc.returncode
        print(json.dumps({"status": report["status"], "mode": plan.mode, "returncode": proc.returncode}, sort_keys=True))
        write_report(args.report_json, report)
        return proc.returncode
    finally:
        if overlay_dir is not None and not args.keep_overlay:
            shutil.rmtree(overlay_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
