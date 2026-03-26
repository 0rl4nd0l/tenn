#!/usr/bin/env python3
"""Download PDFs for all documents missing pdf_sha256. Run in tmux."""
import argparse
import logging
import time

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

import httpx
from sqlalchemy import text

from app.core.db import SessionLocal
from app.services.pipeline import download_pdf_for_document

parser = argparse.ArgumentParser()
parser.add_argument("--ticker", required=True, help="Ticker to download PDFs for")
args = parser.parse_args()
TICKER = args.ticker.strip().upper()

db = SessionLocal()
rows = db.execute(
    text("SELECT document_id FROM documents WHERE ticker = :t AND (pdf_sha256 IS NULL OR pdf_sha256 = '')"),
    {"t": TICKER},
).fetchall()

total = len(rows)
print(f"\n{'='*60}", flush=True)
print(f"Download PDFs: {total} {TICKER} documents", flush=True)
print(f"{'='*60}\n", flush=True)

ok = fail = 0
t0 = time.time()
client = httpx.Client(timeout=60.0, follow_redirects=True)

for i, (doc_id,) in enumerate(rows):
    try:
        download_pdf_for_document(db, doc_id, http_client=client)
        ok += 1
    except Exception as e:
        fail += 1
        if fail <= 5:
            print(f"  FAIL [{i+1}/{total}] {doc_id[:8]}.. {str(e)[:80]}", flush=True)
    if (i + 1) % 25 == 0:
        elapsed = time.time() - t0
        print(f"  progress: {i+1}/{total} ok={ok} fail={fail} [{elapsed:.0f}s]", flush=True)

client.close()
db.close()
elapsed = time.time() - t0
print(f"\n{'='*60}", flush=True)
print(f"DONE in {elapsed:.0f}s: ok={ok} fail={fail}", flush=True)
print(f"{'='*60}", flush=True)
