#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = REPO_ROOT / "data" / "asx" / "importance"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove legacy data/asx/importance mirror now that docs/ is the source of truth."
    )
    parser.add_argument(
        "--target",
        default=str(DEFAULT_TARGET),
        help="Directory to remove (default: data/asx/importance).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete target. Without this flag, script is dry-run only.",
    )
    return parser.parse_args()


def _dir_stats(path: Path) -> tuple[int, int]:
    files = 0
    bytes_total = 0
    for p in path.rglob("*"):
        if p.is_file():
            files += 1
            try:
                bytes_total += p.stat().st_size
            except Exception:
                pass
    return files, bytes_total


def main() -> None:
    args = parse_args()
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"[cleanup_importance] target_missing path={target}")
        return
    if not target.is_dir():
        raise SystemExit(f"Target is not a directory: {target}")

    files, bytes_total = _dir_stats(target)
    print(
        f"[cleanup_importance] target={target} files={files} bytes={bytes_total} "
        f"mode={'delete' if args.yes else 'dry_run'}"
    )
    if not args.yes:
        print("[cleanup_importance] dry-run only. Re-run with --yes to delete.")
        return

    shutil.rmtree(target)
    print(f"[cleanup_importance] deleted={target}")


if __name__ == "__main__":
    main()
