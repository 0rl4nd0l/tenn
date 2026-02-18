import base64
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright
from sqlalchemy import func, or_

from app.models.documents import Document
from app.services.storage import sha256_file, write_bytes

BASE_PAGE = "https://www.marketindex.com.au/asx/announcements"
API_ANNOUNCEMENTS_BASE = "https://data-api.marketindex.com.au/api/v1/announcements"

MARKER_HEADED_REQUIRED = "blocked_marketindex_headed_required"
MARKER_403 = "blocked_marketindex_403"
MARKER_NO_CANDIDATE = "blocked_marketindex_no_candidate"
MARKER_HEADED_ERROR = "blocked_marketindex_headed_error"

TARGET_MARKERS = {
    "",
    MARKER_HEADED_REQUIRED,
    MARKER_403,
    MARKER_NO_CANDIDATE,
    MARKER_HEADED_ERROR,
}


def is_pdf_candidate(link):
    if not link:
        return False
    lower = link.lower()
    return "/pdf/" in lower or lower.endswith(".pdf") or ".pdf?" in lower


def extract_announcement_id(value):
    if not value:
        return None
    match = re.search(r"-([0-9A-Z]{8,12})(?:/)?$", str(value).strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()


def slugify_heading(heading):
    if not heading:
        return "announcement"
    slug = heading.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "announcement"


def parse_identifier_from_link(link, fallback_ticker=None):
    if not link:
        return None

    marker = "/api/v1/announcements/"
    if marker in link:
        tail = link.split(marker, 1)[1]
        identifier = tail.split("/", 1)[0] if tail else None
        return identifier or None

    parsed = urlparse(link)
    if "marketindex.com.au" not in parsed.netloc.lower():
        return None

    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(path_parts) < 4 or path_parts[0].lower() != "asx" or path_parts[2].lower() != "announcements":
        return None

    ticker = path_parts[1].upper() if path_parts[1] else None
    if not ticker:
        ticker = (fallback_ticker or "").strip().upper() or None

    announcement_id = extract_announcement_id(path_parts[3]) or extract_announcement_id(parsed.path)
    if not ticker or not announcement_id:
        return None

    return f"XASX:{ticker}:{announcement_id}"


def build_inline_pdf_url(identifier, heading):
    if not identifier:
        return None
    return f"{API_ANNOUNCEMENTS_BASE}/{identifier}/pdf/inline/{slugify_heading(heading)}"


def build_announcement_page_url(source_url, ticker, heading):
    if source_url:
        parsed = urlparse(source_url)
        host = parsed.netloc.lower()
        if host == "www.marketindex.com.au" and "/announcements/" in parsed.path.lower():
            return source_url

    identifier = parse_identifier_from_link(source_url, fallback_ticker=ticker)
    if not identifier:
        return None

    parts = [part for part in identifier.split(":") if part]
    if len(parts) < 3:
        return None

    ticker_slug = parts[1].lower()
    announcement_id = parts[-1]
    slug = slugify_heading(heading)
    return f"https://www.marketindex.com.au/asx/{ticker_slug}/announcements/{slug}-{announcement_id}"


def unique_links(links):
    seen = set()
    deduped = []
    for link in links:
        if not link or link in seen:
            continue
        seen.add(link)
        deduped.append(link)
    return deduped


def build_candidate_links(source_url, ticker, heading):
    identifier = parse_identifier_from_link(source_url, fallback_ticker=ticker)
    inline_link = build_inline_pdf_url(identifier, heading)
    direct_link = source_url if is_pdf_candidate(source_url) else None
    return unique_links([direct_link, inline_link])


def map_failure_marker(outcome):
    fetch_failures = outcome.get("fetch_failures") or []
    if any(item.get("http_status") == 403 for item in fetch_failures):
        return MARKER_403
    return MARKER_HEADED_ERROR


def marker_bucket(value):
    marker = (value or "").strip()
    if marker == "":
        return "empty"
    if marker.startswith("blocked_"):
        return marker
    return "hashed"


def summarize_status_counts(rows):
    counts = Counter()
    for row in rows:
        counts[marker_bucket(row.pdf_sha256)] += 1
    return dict(counts)


def parse_ticker_filters(ticker_values):
    if not ticker_values:
        return []
    parsed = []
    for raw in ticker_values:
        if not raw:
            continue
        for part in str(raw).split(","):
            symbol = part.strip().upper()
            if symbol:
                parsed.append(symbol)
    seen = set()
    deduped = []
    for symbol in parsed:
        if symbol in seen:
            continue
        seen.add(symbol)
        deduped.append(symbol)
    return deduped


async def open_base_page(page):
    attempts = [("networkidle", 90000), ("domcontentloaded", 90000), ("load", 90000)]
    last_error = None
    for wait_mode, timeout in attempts:
        try:
            await page.goto(BASE_PAGE, wait_until=wait_mode, timeout=timeout)
            return wait_mode
        except Exception as error:
            last_error = error
    raise last_error


async def extract_pdf_links_from_announcement_page(page, announcement_url):
    if not announcement_url:
        return []

    return await page.evaluate(
        """
        async (targetUrl) => {
          try {
            const response = await fetch(targetUrl, {
              method: 'GET',
              credentials: 'include',
              headers: { 'Accept': 'text/html,*/*' }
            });
            if (!response.ok) {
              return [];
            }

            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const found = new Set();

            const isPdfLike = (url) => /\\/pdf\\/|\\.pdf(?:$|\\?)/i.test(url);

            for (const anchor of doc.querySelectorAll('a[href]')) {
              const href = anchor.getAttribute('href');
              if (!href) continue;
              try {
                const absolute = new URL(href, targetUrl).toString();
                if (isPdfLike(absolute)) {
                  found.add(absolute);
                }
              } catch (_) {}
            }

            const regexes = [
              /https:\\/\\/data-api\\.marketindex\\.com\\.au\\/api\\/v1\\/announcements\\/[A-Z0-9:]+\\/pdf\\/inline\\/[A-Za-z0-9-]+/gi,
              /https:\\/\\/files\\.marketindex\\.com\\.au\\/[^"'\\s>]+\\.pdf(?:\\?[^"'\\s>]*)?/gi
            ];

            for (const regex of regexes) {
              const matches = html.match(regex) || [];
              for (const match of matches) {
                found.add(match);
              }
            }

            return Array.from(found);
          } catch (_) {
            return [];
          }
        }
        """,
        announcement_url,
    )


async def fetch_pdf_response(page, url):
    fetched = await page.evaluate(
        """
        async (targetUrl) => {
          try {
            const response = await fetch(targetUrl, {
              method: 'GET',
              credentials: 'include',
              headers: { 'Accept': 'application/pdf,*/*' }
            });

            const contentType = response.headers.get('content-type') || '';
            if (!response.ok) {
              const body = await response.text();
              return {
                ok: false,
                status: response.status,
                contentType,
                error: body.slice(0, 300)
              };
            }

            const buffer = await response.arrayBuffer();
            const bytes = new Uint8Array(buffer);
            const chunkSize = 0x8000;
            let binary = '';
            for (let i = 0; i < bytes.length; i += chunkSize) {
              binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
            }

            return {
              ok: true,
              status: response.status,
              contentType,
              base64: btoa(binary)
            };
          } catch (error) {
            return {
              ok: false,
              status: 0,
              contentType: '',
              error: String(error)
            };
          }
        }
        """,
        url,
    )

    if not fetched.get("ok"):
        return fetched

    try:
        data = base64.b64decode(fetched["base64"])
    except Exception as error:
        return {
            "ok": False,
            "status": fetched.get("status"),
            "contentType": fetched.get("contentType"),
            "error": str(error),
        }

    return {
        "ok": True,
        "status": fetched.get("status"),
        "contentType": fetched.get("contentType"),
        "bytes": data,
    }


async def attempt_download_candidate_links(page, candidate_links, target_file):
    fetch_failures = []
    decode_failures = []
    non_pdf_responses = []

    for candidate_link in candidate_links:
        fetched = await fetch_pdf_response(page, candidate_link)
        if not fetched.get("ok"):
            fetch_failures.append(
                {
                    "link": candidate_link,
                    "http_status": fetched.get("status"),
                    "content_type": fetched.get("contentType"),
                    "error": fetched.get("error"),
                }
            )
            continue

        data = fetched.get("bytes")
        if not isinstance(data, (bytes, bytearray)):
            decode_failures.append({"link": candidate_link, "error": "Missing byte payload"})
            continue

        if not data.startswith(b"%PDF"):
            non_pdf_responses.append(
                {
                    "link": candidate_link,
                    "content_type": fetched.get("contentType"),
                    "head_bytes": list(data[:8]),
                }
            )
            continue

        write_bytes(str(target_file), data)
        return {
            "status": "downloaded",
            "bytes": len(data),
            "content_type": fetched.get("contentType"),
            "resolved_link": candidate_link,
        }

    if decode_failures or non_pdf_responses:
        return {
            "status": "failed_invalid_pdf_response",
            "decode_failures": decode_failures[:3],
            "non_pdf_responses": non_pdf_responses[:3],
            "fetch_failures": fetch_failures[:3],
        }

    if fetch_failures:
        status = "skipped_unavailable" if all(item.get("http_status") == 404 for item in fetch_failures) else "failed_fetch"
        return {
            "status": status,
            "fetch_failures": fetch_failures[:3],
        }

    return {"status": "failed_unknown"}


async def recover_marketindex_documents_headed(db, ticker_filters=None, limit=0, dry_run=False, logger=print):
    ticker_filters = parse_ticker_filters(ticker_filters)
    marker_predicate = or_(
        Document.pdf_sha256.is_(None),
        Document.pdf_sha256 == "",
        Document.pdf_sha256.in_(list(TARGET_MARKERS - {""})),
    )
    query = (
        db.query(Document)
        .filter(func.lower(Document.source_url).like("%marketindex.com.au%"))
        .filter(marker_predicate)
        .order_by(Document.published_at.desc().nullslast(), Document.ingested_at.desc().nullslast())
    )

    if ticker_filters:
        query = query.filter(Document.ticker.in_(ticker_filters))
    if limit and limit > 0:
        query = query.limit(limit)

    selected = query.all()
    selected_ids = [row.document_id for row in selected]
    status_counts_before = summarize_status_counts(selected)

    report = {
        "selected_total": len(selected),
        "attempted": 0,
        "recovered": 0,
        "skipped": 0,
        "failed": 0,
        "status_counts_before": status_counts_before,
        "status_counts_after": status_counts_before.copy(),
        "results": [],
    }

    if not selected:
        logger("Headed recovery: no target MarketIndex documents selected.")
        return report

    logger(f"Headed recovery: selected={len(selected)} dry_run={dry_run}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context()
        page = await context.new_page()
        mode = await open_base_page(page)
        logger(f"Headed recovery browser ready (wait_until='{mode}').")

        for row in selected:
            result = {
                "document_id": str(row.document_id),
                "ticker": row.ticker,
                "source_url": row.source_url,
                "outcome": None,
                "error": None,
            }
            heading = row.title or "announcement"
            announcement_url = build_announcement_page_url(row.source_url, row.ticker, heading)
            candidate_links = build_candidate_links(row.source_url, row.ticker, heading)
            if announcement_url:
                page_candidates = await extract_pdf_links_from_announcement_page(page, announcement_url)
                candidate_links = unique_links(candidate_links + page_candidates)

            result["candidate_count"] = len(candidate_links)

            if not candidate_links:
                report["skipped"] += 1
                result["outcome"] = MARKER_NO_CANDIDATE
                if not dry_run:
                    row.pdf_sha256 = MARKER_NO_CANDIDATE
                    db.commit()
                report["results"].append(result)
                continue

            if dry_run:
                report["skipped"] += 1
                result["outcome"] = "dry_run_candidate_resolved"
                report["results"].append(result)
                continue

            report["attempted"] += 1
            try:
                outcome = await attempt_download_candidate_links(page, candidate_links, Path(row.pdf_path))
                status = outcome.get("status")

                if status == "downloaded":
                    row.pdf_sha256 = sha256_file(row.pdf_path)
                    db.commit()
                    report["recovered"] += 1
                    result["outcome"] = "downloaded"
                    result["bytes"] = outcome.get("bytes")
                    result["resolved_link"] = outcome.get("resolved_link")
                else:
                    marker = map_failure_marker(outcome)
                    row.pdf_sha256 = marker
                    db.commit()
                    report["failed"] += 1
                    result["outcome"] = marker
                    result["error"] = outcome.get("fetch_failures") or outcome.get("status")
            except Exception as error:
                row.pdf_sha256 = MARKER_HEADED_ERROR
                db.commit()
                report["failed"] += 1
                result["outcome"] = MARKER_HEADED_ERROR
                result["error"] = str(error)

            report["results"].append(result)

        await browser.close()

    refreshed = db.query(Document).filter(Document.document_id.in_(selected_ids)).all()
    report["status_counts_after"] = summarize_status_counts(refreshed)
    return report
