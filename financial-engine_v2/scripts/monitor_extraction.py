#!/usr/bin/env python3
"""
Monitor extraction progress for a ticker and notify on completion.
Polls the log file and DB every 60s. Sends desktop notification when done.
Run in a separate tmux pane.
"""
import argparse
import subprocess
import time
from pathlib import Path

from sqlalchemy import create_engine, text

DB_URL = "sqlite:////home/l4nd0/tenn/financial-engine_v2/data/fe_local.db"
engine = create_engine(DB_URL)

parser = argparse.ArgumentParser()
parser.add_argument("--ticker", default="RIO")
parser.add_argument("--log", default="/tmp/batch_extract_rio.log")
parser.add_argument("--poll", type=int, default=60, help="Poll interval seconds")
args = parser.parse_args()


def notify(title, msg):
    # Try notify-send (Linux desktop), fall back to terminal bell + print
    try:
        subprocess.run(["notify-send", title, msg], timeout=5)
    except Exception:
        pass
    print(f"\a\U0001f514 {title}: {msg}", flush=True)


def get_counts():
    with engine.connect() as c:
        total = c.execute(
            text("SELECT COUNT(*) FROM documents WHERE ticker=:t AND pdf_sha256 IS NOT NULL"),
            {"t": args.ticker},
        ).scalar()
        done = c.execute(
            text(
                "SELECT COUNT(*) FROM extraction_runs er"
                " JOIN documents d ON d.document_id=er.document_id"
                " WHERE d.ticker=:t"
            ),
            {"t": args.ticker},
        ).scalar()
        risk = c.execute(
            text(
                "SELECT COUNT(*) FROM asx_risk_notes rn"
                " JOIN documents d ON d.document_id=rn.document_id"
                " WHERE d.ticker=:t"
            ),
            {"t": args.ticker},
        ).scalar()
        fins = c.execute(
            text("SELECT COUNT(*) FROM asx_periodic_financials WHERE ticker=:t"),
            {"t": args.ticker},
        ).scalar()
    return total, done, risk, fins


print(f"Monitoring {args.ticker} extraction. Poll every {args.poll}s. Ctrl+C to stop.", flush=True)

prev_done = 0
while True:
    try:
        total, done, risk, fins = get_counts()
        log_lines = Path(args.log).read_text().count("\n") if Path(args.log).exists() else 0
        print(
            f"  [{time.strftime('%H:%M:%S')}] {done}/{total} extracted"
            f" | risk_notes={risk} financials={fins} | log_lines={log_lines}",
            flush=True,
        )

        if done > prev_done:
            prev_done = done

        if done >= total and total > 0:
            notify(
                f"{args.ticker} extraction complete",
                f"{done}/{total} docs extracted. risk_notes={risk} financials={fins}",
            )
            print(
                f"\n\u2705 DONE — {done}/{total} extracted."
                f" Run re_embed_docs.py --ticker {args.ticker} next.",
                flush=True,
            )
            break

        time.sleep(args.poll)
    except KeyboardInterrupt:
        print("\nMonitor stopped.", flush=True)
        break
