#!/usr/bin/env python3
"""Backfill announcement_type for existing Document rows where it is NULL.

Uses the deterministic classify_announcement() function (keyword-based, no LLM).
Safe to run repeatedly — only touches rows with NULL announcement_type.

Usage:
    python scripts/backfill_announcement_type.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.db import SessionLocal
from app.models.documents import Document
from app.services.announcement_importance import classify_announcement


def main():
    parser = argparse.ArgumentParser(description="Backfill announcement_type on documents")
    parser.add_argument("--dry-run", action="store_true", help="Print classifications without updating DB")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = db.query(Document).filter(Document.announcement_type.is_(None)).all()
        print(f"Found {len(rows)} documents with NULL announcement_type")

        if not rows:
            print("Nothing to backfill.")
            return

        counts: Counter[str] = Counter()
        for doc in rows:
            result = classify_announcement(
                title=doc.title,
                doc_class=doc.doc_class,
                doc_subtype=doc.doc_subtype,
                pdf_excerpt=None,
            )
            label = result.get("label", "other")
            counts[label] += 1

            if args.dry_run:
                print(f"  {doc.ticker:>6s} | {label:<30s} | {doc.title[:60]}")
            else:
                doc.announcement_type = label

        print(f"\nClassification summary:")
        for label, count in counts.most_common():
            print(f"  {label:<35s} {count:>5d}")

        if not args.dry_run:
            db.commit()
            print(f"\nUpdated {len(rows)} rows.")
        else:
            print(f"\n[DRY RUN] No changes written.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
