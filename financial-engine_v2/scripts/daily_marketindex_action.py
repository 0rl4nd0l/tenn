import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _run_metadata import build_run_metadata


DEFAULT_INGEST_SCRIPT = "scripts/marketindex_ingest.py"
DEFAULT_DOWNLOAD_SCRIPT = "scripts/marketindex_download_pdfs.py"
DEFAULT_ANNOUNCEMENTS_FILE = "data/raw/marketindex_announcements.json"
DEFAULT_PDF_DIR = "data/marketindex/pdfs"
DEFAULT_DOWNLOAD_REPORT = "reports/marketindex/pdf_download_report.json"
DEFAULT_DAILY_REPORT = "reports/marketindex/daily_marketindex_action_report.json"


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_step(name, command, workdir):
    started_at = utc_now()
    started_ts = time.time()

    print(f"\n[{name}] running: {' '.join(command)}")
    completed = subprocess.run(command, cwd=workdir, check=False)

    ended_at = utc_now()
    elapsed = round(time.time() - started_ts, 3)

    result = {
        "name": name,
        "command": command,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": elapsed,
        "returncode": completed.returncode,
        "success": completed.returncode == 0,
    }

    if completed.returncode == 0:
        print(f"[{name}] completed in {elapsed}s")
    else:
        print(f"[{name}] failed with code {completed.returncode}")

    return result


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run the full daily MarketIndex announcement action (ingest + PDF downloads)."
    )
    parser.add_argument("--python", default=sys.executable, help="Python executable to run child scripts.")
    parser.add_argument("--ingest-script", default=DEFAULT_INGEST_SCRIPT, help="Ingestion script path.")
    parser.add_argument("--download-script", default=DEFAULT_DOWNLOAD_SCRIPT, help="PDF download script path.")
    parser.add_argument("--announcements-file", default=DEFAULT_ANNOUNCEMENTS_FILE, help="Announcements JSON path.")
    parser.add_argument("--pdf-dir", default=DEFAULT_PDF_DIR, help="Output directory for downloaded PDFs.")
    parser.add_argument("--download-report", default=DEFAULT_DOWNLOAD_REPORT, help="PDF download report path.")
    parser.add_argument("--daily-report", default=DEFAULT_DAILY_REPORT, help="Daily action summary report path.")
    parser.add_argument(
        "--download-limit",
        type=int,
        default=0,
        help="Limit number of announcements to attempt PDF download for (0 = no limit).",
    )
    parser.add_argument("--overwrite-pdfs", action="store_true", help="Overwrite existing PDF files.")
    parser.add_argument("--headless-download", action="store_true", help="Use headless browser for download step.")
    parser.add_argument("--skip-download", action="store_true", help="Only run ingestion.")
    parser.add_argument(
        "--min-download-count",
        type=int,
        default=5,
        help="Quality gate minimum downloaded file count for download step.",
    )
    parser.add_argument(
        "--min-success-ratio",
        type=float,
        default=0.35,
        help="Quality gate minimum success ratio for download step.",
    )
    parser.add_argument(
        "--null-retry-delay-seconds",
        type=int,
        default=15,
        help="Delay before one secondary pass for unresolved announcements.",
    )
    parser.add_argument(
        "--ingest-max-pages",
        type=int,
        default=8,
        help="Max pages for MarketIndex ingest step (0 = all pages).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan/estimates and exit without writing files.",
    )
    return parser


def main():
    args = build_parser().parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    ingest_script = repo_root / args.ingest_script
    download_script = repo_root / args.download_script
    daily_report_path = repo_root / args.daily_report

    ingest_cmd = [args.python, str(ingest_script), "--output", args.announcements_file]
    if args.ingest_max_pages and args.ingest_max_pages > 0:
        ingest_cmd.extend(["--max-pages", str(args.ingest_max_pages)])

    download_cmd = None
    if not args.skip_download:
        download_cmd = [
            args.python,
            str(download_script),
            "--input",
            args.announcements_file,
            "--output-dir",
            args.pdf_dir,
            "--report",
            args.download_report,
        ]
        if args.download_limit > 0:
            download_cmd.extend(["--limit", str(args.download_limit)])
        if args.overwrite_pdfs:
            download_cmd.append("--overwrite")
        download_cmd.extend(["--min-download-count", str(args.min_download_count)])
        download_cmd.extend(["--min-success-ratio", str(args.min_success_ratio)])
        download_cmd.extend(["--null-retry-delay-seconds", str(args.null_retry_delay_seconds)])

    if args.dry_run:
        plan = {
            "dry_run": True,
            "script": "daily_marketindex_action",
            "settings": {
                "ingest_script": str(ingest_script),
                "download_script": str(download_script),
                "announcements_file": args.announcements_file,
                "pdf_dir": args.pdf_dir,
                "download_report": args.download_report,
                "daily_report": str(daily_report_path),
                "download_limit": args.download_limit,
                "overwrite_pdfs": bool(args.overwrite_pdfs),
                "skip_download": bool(args.skip_download),
                "min_download_count": args.min_download_count,
                "min_success_ratio": args.min_success_ratio,
                "null_retry_delay_seconds": args.null_retry_delay_seconds,
                "ingest_max_pages": args.ingest_max_pages,
            },
            "commands": {
                "ingest": ingest_cmd,
                "download": download_cmd,
            },
        }
        print(json.dumps(plan, indent=2, default=str))
        return

    daily_report_path.parent.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = {
        "run_id": run_id,
        "started_at": utc_now(),
        "run_metadata": build_run_metadata(repo_root, __file__),
        "settings": {
            "python": args.python,
            "ingest_script": args.ingest_script,
            "download_script": args.download_script,
            "announcements_file": args.announcements_file,
            "pdf_dir": args.pdf_dir,
            "download_report": args.download_report,
            "download_limit": args.download_limit,
            "overwrite_pdfs": args.overwrite_pdfs,
            "headless_download": args.headless_download,
            "skip_download": args.skip_download,
            "min_download_count": args.min_download_count,
            "min_success_ratio": args.min_success_ratio,
            "null_retry_delay_seconds": args.null_retry_delay_seconds,
            "ingest_max_pages": args.ingest_max_pages,
        },
        "steps": [],
    }

    if args.headless_download:
        summary["status"] = "failed_config"
        summary["ended_at"] = utc_now()
        summary["steps"].append(
            {
                "name": "config_validation",
                "success": False,
                "reason": "--headless-download is unsupported for MarketIndex due to anti-bot protections.",
            }
        )
        daily_report_path.write_text(json.dumps(summary, indent=2))
        print(f"\nDaily action failed during config validation. Report: {daily_report_path}")
        raise SystemExit(2)

    if not ingest_script.exists():
        raise FileNotFoundError(f"Ingestion script not found: {ingest_script}")
    if not download_script.exists() and not args.skip_download:
        raise FileNotFoundError(f"Download script not found: {download_script}")

    ingest_result = run_step("ingest_announcements", ingest_cmd, str(repo_root))
    summary["steps"].append(ingest_result)

    if not ingest_result["success"]:
        summary["status"] = "failed_ingest"
        summary["ended_at"] = utc_now()
        daily_report_path.write_text(json.dumps(summary, indent=2))
        print(f"\nDaily action failed during ingestion. Report: {daily_report_path}")
        raise SystemExit(ingest_result["returncode"])

    if not args.skip_download:
        download_result = run_step("download_pdfs", download_cmd, str(repo_root))
        summary["steps"].append(download_result)

        if not download_result["success"]:
            summary["status"] = "failed_download"
            summary["ended_at"] = utc_now()
            daily_report_path.write_text(json.dumps(summary, indent=2))
            print(f"\nDaily action failed during download. Report: {daily_report_path}")
            raise SystemExit(download_result["returncode"])
    else:
        summary["steps"].append(
            {
                "name": "download_pdfs",
                "success": True,
                "skipped": True,
                "reason": "--skip-download enabled",
            }
        )

    summary["status"] = "success"
    summary["ended_at"] = utc_now()
    daily_report_path.write_text(json.dumps(summary, indent=2))
    print(f"\nDaily action completed successfully. Report: {daily_report_path}")


if __name__ == "__main__":
    main()
