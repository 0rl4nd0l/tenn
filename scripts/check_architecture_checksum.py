#!/usr/bin/env python3
"""
Check that key architecture docs have not changed without review.

Hashes docs/architecture/04_ingestion_pipeline.md,
06_embeddings_and_vector_store.md, 08_backfill_contract.md and compares
to docs/architecture/.arch_checksum. Exits 1 on mismatch.

Usage:
  python scripts/check_architecture_checksum.py           # check only
  python scripts/check_architecture_checksum.py --update  # write new checksum
"""

import argparse
import hashlib
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ARCH_DIR = REPO_ROOT / "docs" / "architecture"
CHECKSUM_FILE = ARCH_DIR / ".arch_checksum"

# Ordered for deterministic hash
DOCS = [
    ARCH_DIR / "04_ingestion_pipeline.md",
    ARCH_DIR / "06_embeddings_and_vector_store.md",
    ARCH_DIR / "08_backfill_contract.md",
]


def compute_checksum() -> str:
    h = hashlib.sha256()
    for p in DOCS:
        if not p.exists():
            raise FileNotFoundError(f"Missing architecture doc: {p}")
        h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check architecture docs checksum")
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write current checksum to .arch_checksum (for maintainers)",
    )
    args = parser.parse_args()

    try:
        current = compute_checksum()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.update:
        CHECKSUM_FILE.write_text(current + "\n")
        print(f"Updated {CHECKSUM_FILE}")
        return 0

    if not CHECKSUM_FILE.exists():
        print(
            "Error: No stored checksum at docs/architecture/.arch_checksum.",
            file=sys.stderr,
        )
        return 1

    stored = CHECKSUM_FILE.read_text().strip()
    if current != stored:
        print(
            "Architecture documents changed — ensure migration reviewed.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
