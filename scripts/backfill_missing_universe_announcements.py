#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import socket
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.cli_common import DEFAULT_NEWS_ARTICLES_DB  # noqa: E402

DEFAULT_TICKERS_FILE = REPO_ROOT / "financial-engine_v2" / "data" / "raw" / "asx_ticker_universe.txt"
DEFAULT_FULL_HISTORY_SCRIPT = REPO_ROOT / "financial-engine_v2" / "scripts" / "full_history_ticker_sync.py"
DEFAULT_FULL_HISTORY_HEALTH_JSON = REPO_ROOT / "reports" / "research_engine_health.json"
DEFAULT_OUT_JSON = REPO_ROOT / "reports" / "asx" / "missing_universe_announcement_backfill_plan.json"
DEFAULT_OUT_MISSING_TICKERS = REPO_ROOT / "reports" / "asx" / "missing_universe_tickers.txt"
DEFAULT_FULL_HISTORY_REPORT = REPO_ROOT / "financial-engine_v2" / "reports" / "asx" / "missing_universe_full_history_report.json"
DEFAULT_CHILD_PYTHON = REPO_ROOT / "financial-engine_v2" / ".venv" / "bin" / "python"
DEFAULT_ASX_DNS_HOSTS = (
    "www.asx.com.au",
    "www2.asx.com.au",
    "announcements.asx.com.au",
)
DNS_ERROR_TOKENS = (
    "temporary failure in name resolution",
    "name or service not known",
    "could not resolve host",
    "gaierror",
)

ASX_PATTERN_RE = re.compile(r"\bASX\s*[:\-]\s*([A-Z][A-Z0-9]{1,5})\b", flags=re.IGNORECASE)
AX_SUFFIX_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,5})\.AX(?![A-Za-z0-9])", flags=re.IGNORECASE)
XASX_RE = re.compile(r"\bXASX:([A-Z][A-Z0-9]{1,5})\b", flags=re.IGNORECASE)
URL_ASX_PATH_RE = re.compile(r"/asx/([a-z0-9]{2,5})/announcements(?:/|$)", flags=re.IGNORECASE)
MAPPED_TICKERS_RE = re.compile(r"(?im)^\s*mapped_tickers\s*=\s*([A-Za-z0-9,;|./:\-\s]+)\s*$")
GENERIC_NON_TICKER_TOKENS = {
    "ASX",
    "ETF",
    "ETFS",
    "MINER",
    "MINERS",
    "STOCK",
    "STOCKS",
    "SHARE",
    "SHARES",
    "INDEX",
    "INDICES",
    "FUND",
    "FUNDS",
}


def _iso_utc_now() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_path(raw: str) -> Path:
    path = Path(str(raw or "").strip()).expanduser()
    if path.is_absolute():
        return path.resolve()
    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (REPO_ROOT / path).resolve()


def _parse_provider_list(raw: str) -> List[str]:
    out: List[str] = []
    for part in str(raw or "").split(","):
        token = part.strip().lower()
        if token and token not in out:
            out.append(token)
    return out


def _default_python_bin() -> str:
    if DEFAULT_CHILD_PYTHON.exists() and DEFAULT_CHILD_PYTHON.is_file():
        # Keep the venv launcher path (do not resolve symlink to system python).
        return str(DEFAULT_CHILD_PYTHON)
    return str(Path(sys.executable).resolve())


def _normalize_ticker(value: Any) -> str:
    txt = str(value or "").strip().upper()
    if not txt:
        return ""
    txt = txt.replace("ASX:", "").replace("ASX-", "")
    if "." in txt:
        txt = txt.split(".", 1)[0]
    txt = "".join(ch for ch in txt if ch.isalnum())
    if len(txt) < 2 or len(txt) > 5:
        return ""
    if txt in GENERIC_NON_TICKER_TOKENS:
        return ""
    return txt


def load_ticker_universe(path: Path) -> List[str]:
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"Ticker universe not found: {path}")
    out: List[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        base = line.split("#", 1)[0].strip()
        if not base:
            continue
        sym = _normalize_ticker(base)
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def _extract_candidate_signals(*, title: str, description: str, body: str, canonical_url: str) -> Dict[str, set[str]]:
    by_ticker: Dict[str, set[str]] = {}

    def _add(raw_ticker: str, signal: str) -> None:
        ticker = _normalize_ticker(raw_ticker)
        if not ticker:
            return
        by_ticker.setdefault(ticker, set()).add(signal)

    payload = "\n".join(part for part in (title, description, body, canonical_url) if str(part or "").strip())
    for match in ASX_PATTERN_RE.finditer(payload):
        _add(match.group(1), "asx_tag")
    for match in AX_SUFFIX_RE.finditer(payload):
        _add(match.group(1), "ax_suffix")
    for match in XASX_RE.finditer(payload):
        _add(match.group(1), "xasx_tag")
    for match in URL_ASX_PATH_RE.finditer(canonical_url):
        _add(match.group(1), "url_asx_path")

    for match in MAPPED_TICKERS_RE.finditer(body):
        values = str(match.group(1) or "")
        for token in re.split(r"[\s,;|]+", values):
            _add(token, "mapped_tickers")

    return by_ticker


@dataclass
class TickerEvidence:
    ticker: str
    article_ids: set[str] = field(default_factory=set)
    providers: set[str] = field(default_factory=set)
    signal_counts: Counter[str] = field(default_factory=Counter)
    sample_titles: List[str] = field(default_factory=list)
    earliest_published_at_utc: str = ""
    latest_published_at_utc: str = ""

    def add(
        self,
        *,
        article_id: str,
        provider: str,
        signals: Sequence[str],
        title: str,
        published_at_utc: str,
    ) -> None:
        self.article_ids.add(str(article_id or "").strip())
        provider_txt = str(provider or "").strip().lower()
        if provider_txt:
            self.providers.add(provider_txt)
        for signal in signals:
            self.signal_counts[str(signal)] += 1
        clean_title = str(title or "").strip()
        if clean_title and clean_title not in self.sample_titles and len(self.sample_titles) < 5:
            self.sample_titles.append(clean_title)
        ts = str(published_at_utc or "").strip()
        if ts:
            if not self.earliest_published_at_utc or ts < self.earliest_published_at_utc:
                self.earliest_published_at_utc = ts
            if not self.latest_published_at_utc or ts > self.latest_published_at_utc:
                self.latest_published_at_utc = ts

    def to_payload(self, *, in_universe: bool) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "in_universe": bool(in_universe),
            "article_count": int(len(self.article_ids)),
            "providers": sorted(self.providers),
            "signal_counts": {key: int(val) for key, val in sorted(self.signal_counts.items())},
            "earliest_published_at_utc": self.earliest_published_at_utc,
            "latest_published_at_utc": self.latest_published_at_utc,
            "sample_titles": list(self.sample_titles),
        }


def collect_ticker_evidence(
    *,
    news_articles_db: Path,
    provider_filter: Sequence[str],
    since_utc: str,
) -> tuple[int, Dict[str, TickerEvidence]]:
    conn = sqlite3.connect(str(news_articles_db))
    conn.row_factory = sqlite3.Row
    try:
        where: List[str] = []
        args: List[Any] = []
        providers = [str(item or "").strip().lower() for item in provider_filter if str(item or "").strip()]
        if providers:
            marks = ",".join(["?"] * len(providers))
            where.append(f"provider_best IN ({marks})")
            args.extend(providers)
        if since_utc:
            where.append("published_at_utc >= ?")
            args.append(since_utc)

        sql = (
            "SELECT article_id, provider_best, title, description, body, canonical_url, published_at_utc "
            "FROM articles"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY published_at_utc DESC, article_id DESC"

        rows = conn.execute(sql, tuple(args)).fetchall()
        evidence_by_ticker: Dict[str, TickerEvidence] = {}
        for row in rows:
            article_id = str(row["article_id"] or "").strip()
            provider = str(row["provider_best"] or "").strip().lower()
            title = str(row["title"] or "")
            description = str(row["description"] or "")
            body = str(row["body"] or "")
            canonical_url = str(row["canonical_url"] or "")
            published_at_utc = str(row["published_at_utc"] or "")

            candidates = _extract_candidate_signals(
                title=title,
                description=description,
                body=body,
                canonical_url=canonical_url,
            )
            for ticker, signals in candidates.items():
                slot = evidence_by_ticker.get(ticker)
                if slot is None:
                    slot = TickerEvidence(ticker=ticker)
                    evidence_by_ticker[ticker] = slot
                slot.add(
                    article_id=article_id,
                    provider=provider,
                    signals=sorted(signals),
                    title=title,
                    published_at_utc=published_at_utc,
                )
        return len(rows), evidence_by_ticker
    finally:
        conn.close()


def build_full_history_command(
    *,
    python_bin: str,
    full_history_script: Path,
    tickers: Sequence[str],
    years: int,
    process_documents: bool,
    full_history_report: Path,
    allow_warning: bool,
    health_json_path: Path | None = None,
) -> List[str]:
    cmd = [
        str(python_bin),
        str(full_history_script),
        "--ticker",
        ",".join(sorted({str(item).strip().upper() for item in tickers if str(item).strip()})),
        "--years",
        str(int(max(1, years))),
        "--report",
        str(full_history_report),
    ]
    if process_documents:
        cmd.append("--process-documents")
    if allow_warning:
        cmd.append("--allow-warning")
    if health_json_path is not None:
        cmd.extend(["--health-json", str(health_json_path)])
    return cmd


def _since_utc_from_lookback_days(days: int) -> str:
    lookback = int(days)
    if lookback <= 0:
        return ""
    start = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0) - dt.timedelta(days=lookback)
    return start.isoformat().replace("+00:00", "Z")


def _health_preflight(*, health_json_path: Path, allow_warning: bool) -> Dict[str, Any]:
    resolved = health_json_path.resolve()
    out: Dict[str, Any] = {
        "health_json": str(resolved),
        "allow_warning": bool(allow_warning),
        "status": "",
        "blocked": False,
    }
    if not resolved.exists() or not resolved.is_file():
        out["status"] = "missing"
        out["reason"] = "snapshot_missing"
        return out

    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception as exc:
        out["status"] = "degraded"
        out["blocked"] = True
        out["reason"] = "invalid_json"
        out["error"] = str(exc)
        return out

    status = str((payload or {}).get("overall_status") or "").strip().lower()
    if status not in {"healthy", "warning", "degraded"}:
        out["status"] = "degraded"
        out["blocked"] = True
        out["reason"] = "invalid_schema_missing_overall_status"
        return out

    out["status"] = status
    if status == "degraded":
        out["blocked"] = True
        out["reason"] = "health_gate_degraded"
    elif status == "warning" and not bool(allow_warning):
        out["blocked"] = True
        out["reason"] = "health_gate_warning_without_allow_warning"
    return out


def _dns_preflight(hosts: Sequence[str]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    resolved_count = 0
    for raw_host in hosts:
        host = str(raw_host or "").strip()
        if not host:
            continue
        row: Dict[str, Any] = {"host": host, "resolved": False}
        try:
            addrs = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            ips = sorted({str(item[4][0]) for item in addrs if isinstance(item, tuple) and len(item) >= 5 and item[4]})
            row["resolved"] = True
            row["ip_sample"] = ips[:5]
            resolved_count += 1
        except Exception as exc:
            row["error"] = str(exc)
        checks.append(row)
    blocked = bool(checks) and resolved_count == 0
    out: Dict[str, Any] = {
        "hosts": [str(item.get("host") or "") for item in checks],
        "checks": checks,
        "resolved_host_count": int(resolved_count),
        "blocked": bool(blocked),
    }
    if blocked:
        out["reason"] = "all_dns_lookups_failed"
    return out


def _file_signature(path: Path) -> Dict[str, int] | None:
    if not path.exists() or not path.is_file():
        return None
    stat = path.stat()
    return {
        "size_bytes": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _attach_fresh_full_history_report(
    *,
    execution: Dict[str, Any],
    full_history_report: Path,
    signature_before: Dict[str, int] | None,
) -> None:
    signature_after = _file_signature(full_history_report)
    execution["full_history_report_signature_before"] = signature_before
    execution["full_history_report_signature_after"] = signature_after
    if signature_after is None:
        return
    if signature_before is not None and signature_after == signature_before:
        execution["full_history_report_ignored"] = "unchanged_since_command_start"
        return
    try:
        payload = json.loads(
            full_history_report.read_text(encoding="utf-8")
        )
        execution["full_history_report_payload"] = payload
        marketindex_summary = payload.get("marketindex_headed_recovery") or {}
        if isinstance(marketindex_summary, dict):
            count = int(marketindex_summary.get("requires_headed_recovery_count") or 0)
            command = str(marketindex_summary.get("recommended_command") or "").strip()
            execution["requires_headed_recovery_count"] = count
            if command:
                execution["marketindex_headed_recovery_command"] = command
    except Exception as exc:
        execution["full_history_report_load_error"] = str(exc)


def _looks_like_dns_failure(text: str) -> bool:
    payload = str(text or "").lower()
    if not payload:
        return False
    return any(token in payload for token in DNS_ERROR_TOKENS)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Discover out-of-universe ASX tickers from ingested news articles and optionally "
            "run a 1-year ASX announcement backfill for them."
        )
    )
    ap.add_argument("--news-articles-db", default=str(DEFAULT_NEWS_ARTICLES_DB), help="Path to news_articles SQLite DB.")
    ap.add_argument("--tickers-file", default=str(DEFAULT_TICKERS_FILE), help="ASX ticker universe path.")
    ap.add_argument("--providers", default="", help="Optional comma-separated provider filter, e.g. worldmonitor,gdelt.")
    ap.add_argument("--source-lookback-days", type=int, default=0, help="Only scan articles from last N days (0=all).")
    ap.add_argument("--min-article-count", type=int, default=1, help="Minimum article evidence count per ticker.")
    ap.add_argument("--max-missing-tickers", type=int, default=0, help="Cap missing tickers passed to backfill (0=all).")
    ap.add_argument("--announcement-years", type=int, default=1, help="Announcement backfill window in years.")
    ap.add_argument("--execute", action="store_true", help="Run full_history_ticker_sync for discovered missing tickers.")
    ap.add_argument("--process-documents", action="store_true", help="Pass --process-documents to full_history_ticker_sync.")
    ap.add_argument("--allow-warning", action="store_true", help="Pass --allow-warning to full_history_ticker_sync.")
    ap.add_argument("--full-history-health-json", default="", help="Optional --health-json path passed to full_history_ticker_sync.")
    ap.add_argument(
        "--dns-hosts",
        default=",".join(DEFAULT_ASX_DNS_HOSTS),
        help="Comma-separated hosts used for execute DNS preflight.",
    )
    ap.add_argument("--skip-dns-preflight", action="store_true", help="Skip DNS preflight when --execute is set.")
    ap.add_argument(
        "--execute-retries",
        type=int,
        default=1,
        help="Wrapper-level retries for child execution when non-zero (default 1).",
    )
    ap.add_argument(
        "--execute-retry-delay-seconds",
        type=float,
        default=8.0,
        help="Delay between wrapper-level execute retries.",
    )
    ap.add_argument(
        "--execute-retry-any-error",
        action="store_true",
        help="Retry child execution for any non-zero exit code (default retries only DNS-like failures).",
    )
    ap.add_argument("--python-bin", default=_default_python_bin(), help="Python executable for child workflow.")
    ap.add_argument("--full-history-script", default=str(DEFAULT_FULL_HISTORY_SCRIPT), help="Path to full_history_ticker_sync.py.")
    ap.add_argument("--full-history-report", default=str(DEFAULT_FULL_HISTORY_REPORT), help="Output report path for full_history_ticker_sync.")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="Output JSON plan/result path.")
    ap.add_argument("--out-missing-tickers", default=str(DEFAULT_OUT_MISSING_TICKERS), help="Output TXT file for missing tickers.")
    args = ap.parse_args(argv)

    news_articles_db = _resolve_path(args.news_articles_db)
    tickers_file = _resolve_path(args.tickers_file)
    full_history_script = _resolve_path(args.full_history_script)
    full_history_report = _resolve_path(args.full_history_report)
    full_history_health_json = (
        _resolve_path(args.full_history_health_json)
        if str(args.full_history_health_json or "").strip()
        else DEFAULT_FULL_HISTORY_HEALTH_JSON
    )
    out_json = _resolve_path(args.out_json)
    out_missing_tickers = _resolve_path(args.out_missing_tickers)
    dns_hosts = [host.strip() for host in str(args.dns_hosts or "").split(",") if host.strip()]
    execute_retries = int(max(1, args.execute_retries))
    execute_retry_delay_seconds = float(max(0.0, args.execute_retry_delay_seconds))

    since_utc = _since_utc_from_lookback_days(int(args.source_lookback_days))
    provider_filter = _parse_provider_list(args.providers)
    min_article_count = int(max(1, args.min_article_count))
    max_missing_tickers = int(max(0, args.max_missing_tickers))

    ticker_universe = set(load_ticker_universe(tickers_file))
    articles_scanned, evidence_by_ticker = collect_ticker_evidence(
        news_articles_db=news_articles_db,
        provider_filter=provider_filter,
        since_utc=since_utc,
    )

    in_universe: List[Dict[str, Any]] = []
    missing_universe: List[Dict[str, Any]] = []
    for ticker in sorted(evidence_by_ticker):
        evidence = evidence_by_ticker[ticker]
        if len(evidence.article_ids) < min_article_count:
            continue
        payload = evidence.to_payload(in_universe=(ticker in ticker_universe))
        if ticker in ticker_universe:
            in_universe.append(payload)
        else:
            missing_universe.append(payload)

    in_universe.sort(key=lambda row: (-int(row["article_count"]), str(row["ticker"])))
    missing_universe.sort(key=lambda row: (-int(row["article_count"]), str(row["ticker"])))

    selected_missing = [str(row["ticker"]) for row in missing_universe]
    if max_missing_tickers > 0:
        selected_missing = selected_missing[:max_missing_tickers]

    out_missing_tickers.parent.mkdir(parents=True, exist_ok=True)
    out_missing_tickers.write_text("\n".join(selected_missing) + ("\n" if selected_missing else ""), encoding="utf-8")

    result: Dict[str, Any] = {
        "generated_at_utc": _iso_utc_now(),
        "news_articles_db": str(news_articles_db),
        "tickers_file": str(tickers_file),
        "provider_filter": provider_filter,
        "source_since_utc": since_utc,
        "source_lookback_days": int(args.source_lookback_days),
        "min_article_count": min_article_count,
        "stats": {
            "articles_scanned": int(articles_scanned),
            "candidate_tickers_total": int(len(in_universe) + len(missing_universe)),
            "candidate_tickers_in_universe": int(len(in_universe)),
            "candidate_tickers_missing_universe": int(len(missing_universe)),
            "selected_missing_tickers": int(len(selected_missing)),
        },
        "selected_missing_tickers": selected_missing,
        "out_missing_tickers": str(out_missing_tickers),
        "in_universe_candidates": in_universe,
        "missing_universe_candidates": missing_universe,
        "execution": {
            "requested": bool(args.execute),
            "ran": False,
            "returncode": 0,
            "command": [],
            "full_history_report": str(full_history_report),
            "stdout_tail": [],
            "stderr_tail": [],
            "preflight": {
                "health": {},
                "dns": {
                    "skipped": bool(args.skip_dns_preflight),
                    "hosts": dns_hosts,
                    "checks": [],
                    "resolved_host_count": 0,
                    "blocked": False,
                },
                "blocked_reasons": [],
            },
            "attempts": [],
        },
    }

    exit_code = 0
    if args.execute and selected_missing:
        execution = result["execution"]
        cmd = build_full_history_command(
            python_bin=str(args.python_bin),
            full_history_script=full_history_script,
            tickers=selected_missing,
            years=int(args.announcement_years),
            process_documents=bool(args.process_documents),
            full_history_report=full_history_report,
            allow_warning=bool(args.allow_warning),
            health_json_path=full_history_health_json,
        )
        execution["command"] = cmd

        health_preflight = _health_preflight(
            health_json_path=full_history_health_json,
            allow_warning=bool(args.allow_warning),
        )
        execution["preflight"]["health"] = health_preflight
        if health_preflight.get("blocked"):
            execution["preflight"]["blocked_reasons"].append(str(health_preflight.get("reason") or "health_preflight_blocked"))

        if bool(args.skip_dns_preflight):
            execution["preflight"]["dns"] = {
                "skipped": True,
                "hosts": dns_hosts,
                "checks": [],
                "resolved_host_count": 0,
                "blocked": False,
            }
        else:
            dns_preflight = _dns_preflight(dns_hosts)
            execution["preflight"]["dns"] = dns_preflight
            if dns_preflight.get("blocked"):
                execution["preflight"]["blocked_reasons"].append(str(dns_preflight.get("reason") or "dns_preflight_blocked"))

        if execution["preflight"]["blocked_reasons"]:
            execution["ran"] = False
            execution["success"] = False
            execution["returncode"] = 2
            execution["stderr_tail"] = [
                "Preflight blocked execution.",
                *[str(item) for item in execution["preflight"]["blocked_reasons"]],
            ]
            exit_code = 2
        else:
            report_signature_before = _file_signature(full_history_report)
            _started_ns = time.time_ns()
            cp = None
            for attempt in range(1, execute_retries + 1):
                _attempt_started_ns = time.time_ns()
                cp = subprocess.run(
                    cmd,
                    cwd=str(REPO_ROOT / "financial-engine_v2"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                _attempt_finished_ns = time.time_ns()
                stdout_lines = str(cp.stdout or "").splitlines()
                stderr_lines = str(cp.stderr or "").splitlines()
                combined_tail = "\n".join((stdout_lines + stderr_lines)[-80:])
                dns_like_failure = _looks_like_dns_failure(combined_tail)
                execution["attempts"].append(
                    {
                        "attempt": int(attempt),
                        "returncode": int(cp.returncode),
                        "dns_like_failure": bool(dns_like_failure),
                        "started_epoch_ns": int(_attempt_started_ns),
                        "finished_epoch_ns": int(_attempt_finished_ns),
                        "stdout_tail": stdout_lines[-20:],
                        "stderr_tail": stderr_lines[-20:],
                    }
                )

                if cp.returncode == 0:
                    break
                if attempt >= execute_retries:
                    break
                if not bool(args.execute_retry_any_error) and not dns_like_failure:
                    break
                if execute_retry_delay_seconds > 0:
                    time.sleep(execute_retry_delay_seconds)

            _finished_ns = time.time_ns()
            execution["ran"] = True
            execution["started_epoch_ns"] = int(_started_ns)
            execution["finished_epoch_ns"] = int(_finished_ns)
            if cp is None:
                execution["success"] = False
                execution["returncode"] = 1
                execution["stderr_tail"] = ["Internal error: child process did not execute."]
                exit_code = 1
            else:
                execution["success"] = bool(cp.returncode == 0)
                execution["returncode"] = int(cp.returncode)
                execution["stdout_tail"] = str(cp.stdout or "").splitlines()[-40:]
                execution["stderr_tail"] = str(cp.stderr or "").splitlines()[-40:]
                if cp.returncode != 0:
                    exit_code = 1
            _attach_fresh_full_history_report(
                execution=execution,
                full_history_report=full_history_report,
                signature_before=report_signature_before,
            )
    elif args.execute:
        result["execution"]["success"] = True
    else:
        result["execution"]["success"] = False

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
