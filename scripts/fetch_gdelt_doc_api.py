#!/usr/bin/env python3
"""
Fetch GDELT DOC API articles and emit local JSONL compatible with
scripts/build_news_context_db.py (--input-path mode).
"""

import argparse
import concurrent.futures
import datetime
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
SEENDATE_RE = re.compile(r"^\d{14}$")
SEENDATE_T_RE = re.compile(r"^\d{8}T\d{6}Z$")
DATETIME_RE = re.compile(r"^\d{14}$")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", flags=re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def normalize_space(value: Any) -> str:
    txt = str(value or "").replace("\r", " ").replace("\n", " ")
    return WS_RE.sub(" ", txt).strip()


def normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = raw.replace(" ", "")
    return raw.rstrip("/")


def parse_gdelt_datetime(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if SEENDATE_RE.fullmatch(raw):
        try:
            dt = datetime.datetime.strptime(raw, "%Y%m%d%H%M%S").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return ""
        return dt.isoformat().replace("+00:00", "Z")
    if SEENDATE_T_RE.fullmatch(raw):
        try:
            dt = datetime.datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return ""
        return dt.isoformat().replace("+00:00", "Z")

    candidate = raw
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(candidate)
    except ValueError:
        return ""
    if dt.tzinfo is None:
        return dt.isoformat()
    if dt.utcoffset() == datetime.timedelta(0):
        return dt.isoformat().replace("+00:00", "Z")
    return dt.isoformat()


def iso_date(value: str) -> str:
    txt = str(value or "").strip()
    if not txt:
        return ""
    if "T" in txt:
        try:
            dt = datetime.datetime.fromisoformat(txt.replace("Z", "+00:00"))
            return dt.date().isoformat()
        except ValueError:
            return ""
    try:
        return datetime.date.fromisoformat(txt).isoformat()
    except ValueError:
        return ""


def valid_doc_api_datetime(value: str) -> bool:
    txt = str(value or "").strip()
    return bool(DATETIME_RE.fullmatch(txt))


def build_doc_api_url(
    *,
    query: str,
    mode: str,
    max_records: int,
    sort: str,
    timespan: str,
    start_datetime: str,
    end_datetime: str,
    api_url: str,
) -> str:
    if not str(query).strip():
        raise ValueError("query is required")
    if timespan and (start_datetime or end_datetime):
        raise ValueError("use either --timespan or --start-datetime/--end-datetime, not both")
    if start_datetime and not valid_doc_api_datetime(start_datetime):
        raise ValueError("--start-datetime must be YYYYMMDDHHMMSS")
    if end_datetime and not valid_doc_api_datetime(end_datetime):
        raise ValueError("--end-datetime must be YYYYMMDDHHMMSS")
    if start_datetime and end_datetime and start_datetime > end_datetime:
        raise ValueError("--start-datetime cannot be after --end-datetime")

    params: Dict[str, str] = {
        "query": str(query).strip(),
        "mode": str(mode).strip() or "ArtList",
        "maxrecords": str(max(1, min(250, int(max_records)))),
        "format": "json",
        "sort": str(sort).strip() or "datedesc",
    }
    if timespan:
        params["timespan"] = str(timespan).strip()
    else:
        if start_datetime:
            params["startdatetime"] = str(start_datetime).strip()
        if end_datetime:
            params["enddatetime"] = str(end_datetime).strip()

    return f"{api_url.rstrip('?')}?{urllib.parse.urlencode(params)}"


def request_json(url: str, timeout: float, user_agent: str) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=max(1.0, float(timeout))) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GDELT request failed: {exc}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("GDELT response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("GDELT response JSON root was not an object")
    return payload


def extract_articles(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = payload.get("articles")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def html_to_text(raw: str) -> str:
    cleaned = SCRIPT_STYLE_RE.sub(" ", str(raw or ""))
    cleaned = TAG_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    return normalize_space(cleaned)


def fetch_article_text(url: str, timeout: float, max_chars: int, user_agent: str) -> str:
    if not url:
        return ""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=max(1.0, float(timeout))) as resp:
            # Allow enough bytes for markup overhead but keep memory bounded.
            raw_bytes = resp.read(max(4096, int(max_chars) * 6))
            charset = resp.headers.get_content_charset() or "utf-8"
            content_type = str(resp.headers.get("Content-Type", "")).lower()
    except Exception:
        return ""
    text = raw_bytes.decode(charset, errors="replace")
    if "html" in content_type or "<html" in text[:400].lower():
        text = html_to_text(text)
    else:
        text = normalize_space(text)
    return text[: max(1, int(max_chars))]


def fetch_article_text_map(
    urls: Sequence[str],
    *,
    timeout: float,
    max_chars: int,
    user_agent: str,
    workers: int,
) -> Tuple[Dict[str, str], Dict[str, int]]:
    unique_urls = sorted({normalize_url(url) for url in urls if normalize_url(url)})
    out: Dict[str, str] = {}
    stats = {"requested": len(unique_urls), "ok": 0, "empty": 0}
    if not unique_urls:
        return out, stats

    def _load(target: str) -> Tuple[str, str]:
        return target, fetch_article_text(target, timeout=timeout, max_chars=max_chars, user_agent=user_agent)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        for url, text in pool.map(_load, unique_urls):
            if text:
                out[url] = text
                stats["ok"] += 1
            else:
                stats["empty"] += 1
    return out, stats


def build_body_text(article: Dict[str, Any], full_text: str) -> str:
    title = normalize_space(article.get("title"))
    snippet = normalize_space(
        article.get("snippet")
        or article.get("context")
        or article.get("description")
        or article.get("summary")
    )
    body = normalize_space(full_text)
    if body:
        if title and title.lower() not in body[: max(600, len(title) * 3)].lower():
            return f"{title}\n\n{body}".strip()
        return body
    if title and snippet:
        return f"{title}\n\n{snippet}".strip()
    return title or snippet


def normalize_article_row(
    *,
    article: Dict[str, Any],
    query: str,
    source_label: str,
    topic: str,
    full_text: str,
    min_body_chars: int,
    include_raw: bool,
) -> Tuple[Optional[Dict[str, Any]], str]:
    url = normalize_url(article.get("url"))
    title = normalize_space(article.get("title"))
    if not title and not url:
        return None, "missing_identity"

    published_at = parse_gdelt_datetime(article.get("seendate") or article.get("date") or "")
    doc_date = iso_date(published_at)
    domain = normalize_space(article.get("domain"))
    source_country = normalize_space(article.get("sourcecountry") or article.get("sourceCountry"))
    language = normalize_space(article.get("language"))

    source = domain or source_label or "GDELT"
    body = build_body_text(article=article, full_text=full_text)
    if len(body) < max(1, int(min_body_chars)):
        return None, "short_body"

    seed = url or f"{title}\n{published_at}\n{source}\n{query}"
    record_id = "gdelt_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:24]

    extra: Dict[str, Any] = {
        "provider": "gdelt_doc_api",
        "query": query,
        "domain": domain,
        "source_country": source_country,
        "language": language,
        "seendate_raw": normalize_space(article.get("seendate") or ""),
    }
    if include_raw:
        extra["raw_gdelt_article"] = article

    out = {
        "id": record_id,
        "published_at": published_at,
        "date": doc_date,
        "title": title,
        "text": body,
        "source": source,
        "topic": topic or query,
        "url": url,
        "extra_fields": extra,
    }
    return out, "ok"


def write_jsonl(rows: Iterable[Dict[str, Any]], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch GDELT DOC API records and output JSONL for build_news_context_db.py")
    ap.add_argument("--query", required=True, help="GDELT query expression")
    ap.add_argument("--out", default="reports/news_eval_input/gdelt_doc.jsonl", help="Output JSONL path")
    ap.add_argument("--max-records", type=int, default=250, help="Max records per API call (1-250)")
    ap.add_argument("--timespan", default="7days", help="Relative window like 24h / 7days / 1week / 3months")
    ap.add_argument("--start-datetime", default="", help="Absolute UTC start (YYYYMMDDHHMMSS)")
    ap.add_argument("--end-datetime", default="", help="Absolute UTC end (YYYYMMDDHHMMSS)")
    ap.add_argument("--mode", default="ArtList", help="DOC API mode (ArtList required for row export)")
    ap.add_argument("--sort", default="datedesc", help="DOC API sort mode")
    ap.add_argument("--source-label", default="GDELT DOC 2.0", help="Fallback source label if domain is missing")
    ap.add_argument("--topic", default="", help="Topic label written to output rows (defaults to --query)")
    ap.add_argument("--skip-article-fetch", action="store_true", help="Skip URL backfill and keep only GDELT snippet/title text")
    ap.add_argument("--article-workers", type=int, default=6, help="Concurrent URL fetch workers")
    ap.add_argument("--article-timeout", type=float, default=20.0, help="Per-article fetch timeout seconds")
    ap.add_argument("--article-max-chars", type=int, default=12000, help="Max extracted chars per article")
    ap.add_argument("--request-timeout", type=float, default=60.0, help="GDELT API timeout seconds")
    ap.add_argument("--min-body-chars", type=int, default=200, help="Drop rows whose final text body is shorter than this")
    ap.add_argument("--include-raw", action="store_true", help="Include raw GDELT article objects under extra_fields")
    ap.add_argument("--api-url", default=DOC_API_URL, help="GDELT DOC API endpoint")
    ap.add_argument("--user-agent", default="tenn-gdelt-ingest/1.0", help="HTTP User-Agent header")
    args = ap.parse_args()

    if str(args.mode).strip().lower() != "artlist":
        print("This exporter currently supports only --mode ArtList.", file=sys.stderr)
        return 2

    try:
        url = build_doc_api_url(
            query=args.query,
            mode=args.mode,
            max_records=args.max_records,
            sort=args.sort,
            timespan=args.timespan,
            start_datetime=args.start_datetime,
            end_datetime=args.end_datetime,
            api_url=args.api_url,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        payload = request_json(url, timeout=args.request_timeout, user_agent=args.user_agent)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    articles = extract_articles(payload)
    if not articles:
        print("No articles returned from GDELT API.", file=sys.stderr)
        return 1

    url_list = [normalize_url(row.get("url")) for row in articles if isinstance(row, dict)]
    article_text_map: Dict[str, str] = {}
    fetch_stats = {"requested": 0, "ok": 0, "empty": 0}
    if not args.skip_article_fetch:
        article_text_map, fetch_stats = fetch_article_text_map(
            url_list,
            timeout=args.article_timeout,
            max_chars=args.article_max_chars,
            user_agent=args.user_agent,
            workers=args.article_workers,
        )

    stats: Dict[str, int] = {
        "gdelt_articles": len(articles),
        "kept_rows": 0,
        "dropped_missing_identity": 0,
        "dropped_short_body": 0,
    }
    output_rows: List[Dict[str, Any]] = []
    for row in articles:
        if not isinstance(row, dict):
            continue
        url_key = normalize_url(row.get("url"))
        text = article_text_map.get(url_key, "")
        normalized, reason = normalize_article_row(
            article=row,
            query=args.query,
            source_label=args.source_label,
            topic=args.topic,
            full_text=text,
            min_body_chars=args.min_body_chars,
            include_raw=args.include_raw,
        )
        if normalized is None:
            stats[f"dropped_{reason}"] = stats.get(f"dropped_{reason}", 0) + 1
            continue
        output_rows.append(normalized)
    stats["kept_rows"] = len(output_rows)

    out_path = Path(args.out).expanduser()
    count = write_jsonl(output_rows, out_path)

    report: Dict[str, Any] = {
        "out_path": str(out_path),
        "gdelt_query_url": url,
        "stats": stats,
        "article_fetch": fetch_stats,
    }
    print(json.dumps(report, indent=2))

    if count <= 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
