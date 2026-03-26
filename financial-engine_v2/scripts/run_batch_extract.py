#!/usr/bin/env python3
"""Batch extract all unprocessed BHP documents. Run in tmux."""
import logging, time, sys
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from sqlalchemy import create_engine, text
from app.services.pipeline import process_document

DB_URL = "sqlite:////home/l4nd0/tenn/financial-engine_v2/data/fe_local.db"
engine = create_engine(DB_URL)

with engine.connect() as c:
    rows = c.execute(text("""
        SELECT d.document_id, d.doc_class, d.doc_subtype, d.title
        FROM documents d
        WHERE d.ticker = 'BHP' AND d.pdf_sha256 IS NOT NULL
          AND d.document_id NOT IN (SELECT document_id FROM extraction_runs)
        ORDER BY d.published_at DESC
    """)).fetchall()

total = len(rows)
print(f"\n{'='*60}", flush=True)
print(f"Batch extract: {total} unprocessed BHP documents", flush=True)
print(f"{'='*60}\n", flush=True)

ok = fail = skip = 0
t0 = time.time()

for i, (doc_id, cls, sub, title) in enumerate(rows):
    label = f"[{i+1}/{total}] {doc_id[:8]}.. {cls}/{sub or '-'}: {title[:50]}"
    try:
        r = process_document(doc_id)
        status = (r or {}).get("status") or "no_status"
        structured = (r or {}).get("structured", {})
        has_risk = bool(structured.get("risk_summary"))
        has_fins = bool(structured.get("revenue") or structured.get("operating_cf"))
        elapsed_doc = time.time() - t0
        avg = elapsed_doc / (i + 1)

        if status in ("ok", "ok_low_confidence"):
            ok += 1
            print(f"  OK   {label} risk={'Y' if has_risk else 'N'} fins={'Y' if has_fins else 'N'} [{avg:.1f}s/doc]", flush=True)
        else:
            skip += 1
            print(f"  SKIP {label} status={status} [{avg:.1f}s/doc]", flush=True)
    except Exception as e:
        fail += 1
        print(f"  FAIL {label} {str(e)[:80]}", flush=True)

elapsed = time.time() - t0

# Final DB tally
with engine.connect() as c:
    extr = c.execute(text('SELECT COUNT(*) FROM extraction_runs')).scalar()
    risk_ct = c.execute(text('SELECT COUNT(*) FROM asx_risk_notes')).scalar()
    fins_ct = c.execute(text('SELECT COUNT(*) FROM asx_periodic_financials')).scalar()

print(f"\n{'='*60}", flush=True)
print(f"DONE in {elapsed:.0f}s ({elapsed/60:.1f}m)", flush=True)
print(f"ok={ok} fail={fail} skip={skip}", flush=True)
print(f"DB totals: extraction_runs={extr} risk_notes={risk_ct} financials={fins_ct}", flush=True)
print(f"{'='*60}", flush=True)
