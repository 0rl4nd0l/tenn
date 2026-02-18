#!/usr/bin/env python3
import argparse
from pathlib import Path

from app.core.db import SessionLocal
from app.models.documents import Document
from app.services.pipeline import _doc_path


def _parse_tickers(values):
    if not values:
        return []
    tickers = []
    for raw in values:
        for token in raw.split(","):
            token = token.strip().upper()
            if token:
                tickers.append(token)
    # Keep first-seen order, remove duplicates.
    seen = set()
    ordered = []
    for ticker in tickers:
        if ticker in seen:
            continue
        seen.add(ticker)
        ordered.append(ticker)
    return ordered


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rename stored PDFs to readable date/title filenames and update documents.pdf_path."
    )
    parser.add_argument(
        "--ticker",
        action="append",
        help="Optional ticker filter. Repeat or pass comma-separated values.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max rows to process (0 = all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned renames without changing files/DB.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    tickers = _parse_tickers(args.ticker)

    db = SessionLocal()
    try:
        query = db.query(Document).order_by(Document.ticker.asc(), Document.published_at.desc().nullslast())
        if tickers:
            query = query.filter(Document.ticker.in_(tickers))
        if args.limit and args.limit > 0:
            query = query.limit(args.limit)
        rows = query.all()

        scanned = 0
        renamed = 0
        skipped_missing = 0
        unchanged = 0
        errors = 0

        for doc in rows:
            scanned += 1
            source = Path(doc.pdf_path or "")
            if not source.exists():
                skipped_missing += 1
                continue

            target = Path(
                _doc_path(
                    ticker=doc.ticker,
                    doc_id=str(doc.document_id),
                    published_at=doc.published_at,
                    title=doc.title,
                )
            )
            if source == target:
                unchanged += 1
                continue

            try:
                if not args.dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source.rename(target)
                    doc.pdf_path = str(target)
                renamed += 1
            except Exception:
                errors += 1

        if not args.dry_run:
            db.commit()

        print(
            {
                "scanned": scanned,
                "renamed": renamed,
                "unchanged": unchanged,
                "skipped_missing": skipped_missing,
                "errors": errors,
                "dry_run": args.dry_run,
                "tickers": tickers,
            }
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
