#!/usr/bin/env python3
"""Tenn storage invariants — pure validation before any heavy runtime startup.

This module must not mount disks, mutate paths, or import application code.
Call from shell entrypoints via python3 (preferred) or python.

Environment:
  TENN_CANONICAL_ROOT   Override repo root path (default: /home/l4nd0/tenn)
  TENN_STORAGE_GUARD_SKIP=1   Explicitly skip checks (stderr warning; for non-prod only)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CANONICAL_ROOT = Path(
    os.environ.get("TENN_CANONICAL_ROOT", "/home/l4nd0/tenn")
)


@dataclass
class StorageGuardResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def check_mount(mount_path: str | Path) -> tuple[bool, str]:
    """Return (ok, detail). True if path exists, is a directory, and is a mount point."""
    path = Path(mount_path)
    if not path.exists():
        return False, f"path does not exist: {path}"
    if not path.is_dir():
        return False, f"not a directory: {path}"
    parent = path.parent
    if not parent.exists():
        return False, f"parent missing for mount check: {parent}"
    try:
        st_m = os.stat(path, follow_symlinks=True)
        st_p = os.stat(parent, follow_symlinks=True)
    except OSError as exc:
        return False, f"stat failed: {exc}"
    if st_m.st_dev == st_p.st_dev:
        return (
            False,
            f"{path} is on the same filesystem as {parent} (not mounted — "
            f"often an empty directory on root FS after reboot). "
            f"Mount the data volume on {path} (see /etc/fstab).",
        )
    return True, ""


def check_path_exists(path: str | Path, *, label: str) -> tuple[bool, str]:
    p = Path(path)
    if not p.exists():
        return False, f"{label}: missing path {p}"
    if not p.is_dir():
        return False, f"{label}: not a directory: {p}"
    return True, ""


def validate_tenn_storage(*, canonical_root: Path | None = None) -> StorageGuardResult:
    """Verify critical mounts and Tenn directory layout. Pure; no side effects."""
    errors: list[str] = []
    warnings: list[str] = []

    root = Path(canonical_root or DEFAULT_CANONICAL_ROOT).expanduser().resolve()

    ok, msg = check_mount("/mnt/sdb2")
    if not ok:
        errors.append(f"CRITICAL mount /mnt/sdb2: {msg}")

    ok, msg = check_path_exists(root, label="Tenn canonical repo root")
    if not ok:
        errors.append(f"CRITICAL {msg}")

    fe = root / "financial-engine_v2"
    ok, msg = check_path_exists(fe, label="financial-engine_v2")
    if not ok:
        errors.append(f"CRITICAL {msg}")

    # /mnt/nvme: prefer a dedicated mount (separate st_dev). Many hosts use one NVMe
    # partition for `/` only — then /mnt/nvme is a normal directory on root. That is
    # OK only if the expected runtime tree actually exists (not an empty stub).
    nvme_root = Path("/mnt/nvme")
    if not nvme_root.is_dir():
        errors.append(
            "CRITICAL /mnt/nvme: directory missing. Create it or mount your NVMe volume at /mnt/nvme."
        )
    else:
        nvme_mount_ok, nvme_mount_detail = check_mount("/mnt/nvme")
        nvme_tenn = nvme_root / "tenn"
        ok_t, t_msg = check_path_exists(nvme_tenn, label="/mnt/nvme/tenn")
        if not ok_t:
            errors.append(f"CRITICAL {t_msg}")
        else:
            models = nvme_tenn / "models"
            runtime_data = nvme_tenn / "runtime-data"
            if not models.is_dir() and not runtime_data.is_dir():
                errors.append(
                    "CRITICAL /mnt/nvme/tenn: need at least one of `models/` or `runtime-data/` "
                    "as a directory (inference/runtime layout)."
                )
            elif not nvme_mount_ok:
                warnings.append(
                    "NVMe path /mnt/nvme is not a separate filesystem mount "
                    f"({nvme_mount_detail.strip()}) "
                    "— typical when the whole system lives on one NVMe partition. "
                    "Runtime layout is present (models/ or runtime-data/); continuing. "
                    "If you later add a dedicated NVMe volume, mount it at /mnt/nvme for isolation."
                )

    # Non-critical backup volume
    cold = Path("/mnt/hdd-cold")
    if not cold.exists():
        warnings.append(
            "NON-CRITICAL /mnt/hdd-cold: path missing (backups unavailable; Tenn may still run)."
        )
    else:
        ok_c, cold_msg = check_mount(cold)
        if not ok_c:
            warnings.append(
                f"NON-CRITICAL /mnt/hdd-cold: {cold_msg} "
                "(backups may be on root FS; verify fstab if you rely on cold storage)."
            )

    return StorageGuardResult(ok=(len(errors) == 0), errors=errors, warnings=warnings)


def ensure_tenn_storage_or_exit() -> None:
    """CLI / shell helper: print messages and exit 1 on failure."""
    if os.environ.get("TENN_STORAGE_GUARD_SKIP") == "1":
        print(
            "WARN: TENN_STORAGE_GUARD_SKIP=1 — Tenn storage invariants were NOT checked.",
            file=sys.stderr,
        )
        return

    res = validate_tenn_storage()
    for w in res.warnings:
        print(f"TENN STORAGE WARN: {w}", file=sys.stderr)

    if not res.ok:
        print(
            "TENN STORAGE GUARD: ABORT — required storage is missing, not mounted, or incomplete.\n",
            file=sys.stderr,
        )
        for e in res.errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            "\nSuggested fix:\n"
            "  - Mount primary data: sudo mount UUID=86c817d2-201c-4e8c-8ae3-cfe53b8bdec6 /mnt/sdb2\n"
            "    (and ensure /etc/fstab has a single stable line for that UUID → /mnt/sdb2 without duplicate `/` entries.)\n"
            "  - NVMe runtime: either mount a dedicated volume at /mnt/nvme (fstab), OR on a single-partition\n"
            "    NVMe host ensure directories exist: /mnt/nvme/tenn/models and/or /mnt/nvme/tenn/runtime-data\n"
            "  - Confirm: /home/l4nd0/tenn/financial-engine_v2\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print("TENN STORAGE GUARD: OK (critical mounts and paths present).")


if __name__ == "__main__":
    ensure_tenn_storage_or_exit()
