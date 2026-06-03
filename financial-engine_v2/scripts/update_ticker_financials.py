#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _run_metadata import build_run_metadata

REPO_ROOT = Path(__file__).resolve().parents[1]
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT / "backend"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Update one ticker's financial dataset by discovering announcements, downloading reports, "
            "running extraction, and persisting rows for cockpit retrieval."
        )
    )
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. BHP.")
    parser.add_argument("--years", type=int, default=5, help="History window in years.")
    parser.add_argument("--max-backfill-retries", type=int, default=3, help="Retries for backfill step.")
    parser.add_argument("--resume-max-retries", type=int, default=5, help="Retries for pending-download resume.")
    parser.add_argument(
        "--resume-retry-delay-seconds",
        type=float,
        default=2.0,
        help="Base delay for pending-download retry backoff.",
    )
    parser.add_argument("--process-documents", dest="process_documents", action="store_true")
    parser.add_argument("--no-process-documents", dest="process_documents", action="store_false")
    parser.set_defaults(process_documents=True)
    parser.add_argument(
        "--skip-resume-pending",
        action="store_true",
        help="Skip pending-download resume phase.",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "financial_update_report.json"),
        help="Output path for report JSON.",
    )
    parser.add_argument("--python", default=sys.executable, help="Python executable for child scripts.")
    parser.add_argument(
        "--zero-rows-policy",
        choices=["warn", "fail", "auto_rebuild_fail"],
        default="warn",
        help="Quality gate policy when no financial rows exist after update.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan/estimates and exit without writing DB/files.",
    )
    return parser


def _load_resume_report(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"report_load_error": str(exc), "path": str(path)}


def _query_financial_state(database_url: str, ticker: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"ticker": ticker}
    try:
        from sqlalchemy import create_engine, text  # type: ignore

        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            count_row = conn.execute(
                text("select count(*) as n from asx_periodic_financials where ticker = :ticker"),
                {"ticker": ticker},
            ).mappings().first()
            latest_row = conn.execute(
                text(
                    """
                    select ticker, period_end, period_type, revenue, ebit, np_attributable,
                           operating_cf, investing_cf, financing_cf, capex, cash_end, net_debt,
                           shares_outstanding, confidence_metrics, source_document_id
                    from asx_periodic_financials
                    where ticker = :ticker
                    order by period_end desc
                    limit 1
                    """
                ),
                {"ticker": ticker},
            ).mappings().first()
        payload["rows"] = int((count_row or {}).get("n", 0))
        payload["latest"] = dict(latest_row) if latest_row else None
    except Exception as exc:
        payload["error"] = str(exc)
    return payload


def _extract_pdf_excerpt(pdf_path: Path, max_chars: int = 2000) -> str:
    try:
        import fitz  # type: ignore
    except Exception:
        return ""
    if not pdf_path.exists() or not pdf_path.is_file():
        return ""
    try:
        with fitz.open(pdf_path) as pdf:
            if pdf.page_count < 1:
                return ""
            text = pdf[0].get_text() or ""
    except Exception:
        return ""
    return " ".join(text.split())[:max_chars]


def _refresh_announcement_context(database_url: str, ticker: str, repo_root: Path, limit: int = 40) -> dict[str, Any]:
    stats: dict[str, Any] = {"ticker": ticker, "selected_docs": 0, "upserted": 0}
    try:
        from sqlalchemy import create_engine, text  # type: ignore

        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    create table if not exists cockpit_announcement_context (
                        document_id text primary key,
                        ticker text not null,
                        published_at text,
                        title text,
                        pdf_path text,
                        excerpt text,
                        updated_at text not null
                    )
                    """
                )
            )
            conn.execute(
                text("create index if not exists idx_cockpit_announcement_context_ticker_pub on cockpit_announcement_context(ticker, published_at)")
            )

            rows = conn.execute(
                text(
                    """
                    select document_id, ticker, published_at, title, pdf_path
                    from documents
                    where ticker = :ticker
                    order by published_at desc
                    limit :limit
                    """
                ),
                {"ticker": ticker, "limit": limit},
            ).mappings().all()
            stats["selected_docs"] = len(rows)
            now = utc_now()
            for row in rows:
                rel_pdf_path = str(row.get("pdf_path") or "")
                abs_pdf = Path(rel_pdf_path)
                if not abs_pdf.is_absolute():
                    abs_pdf = (repo_root / abs_pdf).resolve()
                excerpt = _extract_pdf_excerpt(abs_pdf)
                conn.execute(
                    text(
                        """
                        insert into cockpit_announcement_context(document_id, ticker, published_at, title, pdf_path, excerpt, updated_at)
                        values(:document_id, :ticker, :published_at, :title, :pdf_path, :excerpt, :updated_at)
                        on conflict(document_id) do update set
                            ticker=excluded.ticker,
                            published_at=excluded.published_at,
                            title=excluded.title,
                            pdf_path=excluded.pdf_path,
                            excerpt=excluded.excerpt,
                            updated_at=excluded.updated_at
                        """
                    ),
                    {
                        "document_id": str(row.get("document_id")),
                        "ticker": str(row.get("ticker") or ticker),
                        "published_at": str(row.get("published_at") or ""),
                        "title": str(row.get("title") or ""),
                        "pdf_path": rel_pdf_path,
                        "excerpt": excerpt,
                        "updated_at": now,
                    },
                )
                stats["upserted"] += 1
    except Exception as exc:
        stats["error"] = str(exc)
    return stats


def main() -> None:
    args = build_parser().parse_args()

    ticker = args.ticker.strip().upper()
    if not ticker:
        raise SystemExit("--ticker is required")
    if args.years <= 0:
        raise SystemExit("--years must be > 0")
    if args.max_backfill_retries <= 0:
        raise SystemExit("--max-backfill-retries must be > 0")

    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/fe_local.db")
    if bool(getattr(args, "dry_run", False)):
        resume_report = Path(args.report).with_name(f"{Path(args.report).stem}_resume.json")
        resume_cmd = [
            args.python,
            str(REPO_ROOT / "scripts" / "resume_pending_downloads.py"),
            "--ticker",
            ticker,
            "--max-retries",
            str(args.resume_max_retries),
            "--retry-delay-seconds",
            str(args.resume_retry_delay_seconds),
            "--report",
            str(resume_report),
        ]
        if args.process_documents:
            resume_cmd.append("--process-documents")

        rebuild_report = Path(args.report).with_name(f"{Path(args.report).stem}_rebuild.json")
        rebuild_cmd = [
            args.python,
            str(REPO_ROOT / "scripts" / "rebuild_ticker_financials_from_docs.py"),
            "--ticker",
            ticker,
            "--limit",
            "120",
            "--force",
            "--report",
            str(rebuild_report),
        ]

        plan = {
            "dry_run": True,
            "script": "update_ticker_financials",
            "settings": {
                "ticker": ticker,
                "years": args.years,
                "process_documents": bool(args.process_documents),
                "max_backfill_retries": args.max_backfill_retries,
                "resume_max_retries": args.resume_max_retries,
                "resume_retry_delay_seconds": args.resume_retry_delay_seconds,
                "skip_resume_pending": bool(args.skip_resume_pending),
                "zero_rows_policy": args.zero_rows_policy,
                "report": str(args.report),
                "database_url": database_url,
            },
            "before": _query_financial_state(database_url, ticker),
            "resume_command": None if args.skip_resume_pending else resume_cmd,
            "auto_rebuild_command": rebuild_cmd,
            "notes": [
                "Dry-run skips backfill/resume/rebuild execution and does not write reports.",
                "auto_rebuild_command is shown for zero-row quality gate planning only.",
            ],
        }
        print(json.dumps(plan, indent=2, default=str))
        return

    from app.services.pipeline import backfill_ticker_sync  # noqa: E402

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "started_at": utc_now(),
        "run_metadata": build_run_metadata(REPO_ROOT, __file__),
        "settings": {
            "ticker": ticker,
            "years": args.years,
            "process_documents": bool(args.process_documents),
            "max_backfill_retries": args.max_backfill_retries,
            "resume_max_retries": args.resume_max_retries,
            "resume_retry_delay_seconds": args.resume_retry_delay_seconds,
            "resume_pending": not args.skip_resume_pending,
        },
        "database_url": database_url,
        "before": _query_financial_state(database_url, ticker),
        "backfill": None,
        "resume": None,
        "after": None,
        "status": "failed",
    }

    backfill_result: dict[str, Any] | None = None
    backfill_error: str | None = None
    for attempt in range(1, args.max_backfill_retries + 1):
        try:
            print(f"[update] backfill {ticker} attempt {attempt}", flush=True)
            result = backfill_ticker_sync(
                ticker=ticker,
                years=args.years,
                process_documents=bool(args.process_documents),
            )
            result["attempt"] = attempt
            backfill_result = result
            print(
                f"[update] backfill done found={result.get('found')} inserted={result.get('inserted')} "
                f"processed={result.get('processed')} errors={result.get('error_count')}",
                flush=True,
            )
            break
        except Exception as exc:
            backfill_error = str(exc)
            print(f"[update] backfill error on attempt {attempt}: {exc}", flush=True)
            if attempt < args.max_backfill_retries:
                time.sleep(attempt * 2)

    summary["backfill"] = backfill_result or {"failed": True, "error": backfill_error}
    resume_rc = 0

    if not args.skip_resume_pending:
        resume_report = report_path.with_name(f"{report_path.stem}_resume.json")
        resume_cmd = [
            args.python,
            str(REPO_ROOT / "scripts" / "resume_pending_downloads.py"),
            "--ticker",
            ticker,
            "--max-retries",
            str(args.resume_max_retries),
            "--retry-delay-seconds",
            str(args.resume_retry_delay_seconds),
            "--report",
            str(resume_report),
        ]
        if args.process_documents:
            resume_cmd.append("--process-documents")

        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"backend{os.pathsep}{existing_pythonpath}" if existing_pythonpath else "backend"
        env.setdefault("DATABASE_URL", database_url)

        print(f"[update] resume pending: {' '.join(resume_cmd)}", flush=True)
        completed = subprocess.run(resume_cmd, cwd=str(REPO_ROOT), env=env, check=False)
        resume_rc = completed.returncode
        summary["resume"] = {
            "returncode": resume_rc,
            "report_path": str(resume_report),
            "report": _load_resume_report(resume_report),
        }

    summary["after"] = _query_financial_state(database_url, ticker)
    summary["announcement_context"] = _refresh_announcement_context(
        database_url=database_url,
        ticker=ticker,
        repo_root=REPO_ROOT,
        limit=40,
    )

    backfill_errors = int((summary["backfill"] or {}).get("error_count", 0))
    extraction_failed_count = int((summary["backfill"] or {}).get("extraction_failed_count", 0))
    extraction_unknown_count = int((summary["backfill"] or {}).get("extraction_unknown_count", 0))
    after_rows = int((summary.get("after") or {}).get("rows", 0) or 0)
    quality_gate: dict[str, Any] = {
        "policy": args.zero_rows_policy,
        "passed": True,
        "before_rows": int((summary.get("before") or {}).get("rows", 0) or 0),
        "after_rows": after_rows,
        "reasons": [],
        "rebuild": None,
    }

    if after_rows <= 0:
        if args.zero_rows_policy == "warn":
            quality_gate["reasons"].append("Zero financial rows after update; warn mode keeps run successful.")
        elif args.zero_rows_policy == "fail":
            quality_gate["passed"] = False
            quality_gate["reasons"].append("Zero financial rows after update.")
        elif args.zero_rows_policy == "auto_rebuild_fail":
            rebuild_report = report_path.with_name(f"{report_path.stem}_rebuild.json")
            rebuild_cmd = [
                args.python,
                str(REPO_ROOT / "scripts" / "rebuild_ticker_financials_from_docs.py"),
                "--ticker",
                ticker,
                "--limit",
                "120",
                "--force",
                "--report",
                str(rebuild_report),
            ]
            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"backend{os.pathsep}{existing_pythonpath}" if existing_pythonpath else "backend"
            env.setdefault("DATABASE_URL", database_url)
            completed = subprocess.run(rebuild_cmd, cwd=str(REPO_ROOT), env=env, check=False)
            rebuilt_state = _query_financial_state(database_url, ticker)
            quality_gate["rebuild"] = {
                "command": rebuild_cmd,
                "returncode": completed.returncode,
                "report_path": str(rebuild_report),
                "after": rebuilt_state,
            }
            quality_gate["after_rows"] = int((rebuilt_state or {}).get("rows", 0) or 0)
            if completed.returncode != 0 or quality_gate["after_rows"] <= 0:
                quality_gate["passed"] = False
                quality_gate["reasons"].append("Zero financial rows after automatic rebuild.")

    summary["quality_gate"] = quality_gate
    summary["extraction_failures"] = {
        "total": extraction_failed_count,
        "unknown_total": extraction_unknown_count,
        "status_counts": (summary["backfill"] or {}).get("extraction_status_counts", {}),
        "failed": extraction_failed_count > 0 or extraction_unknown_count > 0,
    }
    summary["ended_at"] = utc_now()
    summary["status"] = (
        "success"
        if backfill_result
        and backfill_errors == 0
        and extraction_failed_count == 0
        and extraction_unknown_count == 0
        and resume_rc == 0
        and bool(quality_gate.get("passed"))
        else "failed"
    )

    report_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"[update] status={summary['status']} report={report_path}", flush=True)
    if summary["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
