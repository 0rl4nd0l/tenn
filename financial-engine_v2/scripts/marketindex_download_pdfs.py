import argparse
import asyncio
import base64
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

ANNOUNCEMENTS_FILE = "data/raw/marketindex_announcements.json"
OUTPUT_DIR = "data/marketindex/pdfs"
REPORT_FILE = "reports/marketindex/pdf_download_report.json"
BASE_PAGE = "https://www.marketindex.com.au/asx/announcements"
API_ANNOUNCEMENTS_BASE = "https://data-api.marketindex.com.au/api/v1/announcements"
ROW_SELECTOR = "tbody tr"
HEADER_SELECTOR = "thead th"
NEXT_BUTTON_SELECTOR = "div[data-item-id='next']"

HEADER_ALIASES = {
    "date": {"date"},
    "time": {"time"},
    "ticker": {"ticker", "symbol", "code"},
    "company": {"company", "security", "name"},
    "heading": {"heading", "announcement", "title"},
    "pages": {"pages", "page"},
    "pdf": {"pdf", "document", "file"},
}


def sanitize(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip())


def slugify_heading(heading):
    if not heading:
        return "announcement"
    slug = heading.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "announcement"


def extract_announcement_id(value):
    if not value:
        return None
    match = re.search(r"-([0-9A-Z]{8,12})(?:/)?$", str(value).strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()


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


def build_announcement_page_url(announcement):
    link = announcement.get("link")
    if link:
        parsed = urlparse(link)
        host = parsed.netloc.lower()
        if host == "www.marketindex.com.au" and "/announcements/" in parsed.path.lower():
            return link

    identifier = parse_identifier_from_link(link, fallback_ticker=announcement.get("ticker"))
    if not identifier:
        return None

    parts = [part for part in identifier.split(":") if part]
    if len(parts) < 3:
        return None

    ticker = parts[1].lower()
    announcement_id = parts[-1]
    slug = slugify_heading(announcement.get("heading"))
    return f"https://www.marketindex.com.au/asx/{ticker}/announcements/{slug}-{announcement_id}"


def unique_links(links):
    seen = set()
    deduped = []
    for link in links:
        if not link or link in seen:
            continue
        seen.add(link)
        deduped.append(link)
    return deduped


def build_candidate_links(announcement):
    link = announcement.get("link")
    identifier = parse_identifier_from_link(link, fallback_ticker=announcement.get("ticker"))
    inline_link = build_inline_pdf_url(identifier, announcement.get("heading"))

    direct_link = link if is_pdf_candidate(link) else None
    return unique_links([direct_link, inline_link])


def evaluate_quality_gate(downloaded, candidate_total, min_download_count, min_success_ratio):
    success_ratio = (downloaded / candidate_total) if candidate_total else 0.0
    gate_failed = downloaded < min_download_count and success_ratio < min_success_ratio
    quality_gate = {
        "min_download_count": min_download_count,
        "min_success_ratio": min_success_ratio,
        "passed": not gate_failed,
    }
    if gate_failed:
        quality_gate["reason"] = (
            f"downloaded={downloaded} < min_download_count={min_download_count} "
            f"and success_ratio={success_ratio:.4f} < min_success_ratio={min_success_ratio}"
        )
    return success_ratio, quality_gate, gate_failed


def build_output_path(announcement, index, output_dir):
    link = announcement.get("link")
    identifier = parse_identifier_from_link(link, fallback_ticker=announcement.get("ticker"))

    date_part = sanitize((announcement.get("date") or "unknown-date").replace("/", "-"))
    time_part = sanitize((announcement.get("time") or "unknown-time").replace(":", ""))
    ticker_part = sanitize(announcement.get("ticker") or "UNKNOWN")
    heading_part = sanitize(slugify_heading(announcement.get("heading"))[:96])

    if identifier:
        announcement_id_part = sanitize(identifier.split(":")[-1])
    else:
        announcement_id_part = sanitize(extract_announcement_id(link) or f"{index:04d}")

    name = f"{date_part}_{time_part}_{ticker_part}_{heading_part}_{announcement_id_part}"

    return output_dir / f"{name}.pdf"


def is_pdf_candidate(link):
    if not link:
        return False
    lower = link.lower()
    return "/pdf/" in lower or lower.endswith(".pdf") or ".pdf?" in lower


def normalize_header(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def find_header_index(headers, aliases):
    for idx, header in enumerate(headers):
        for alias in aliases:
            if header == alias or header.startswith(f"{alias} ") or alias in header:
                return idx
    return None


def default_column_map(column_count):
    if column_count >= 7:
        return {
            "date": 0,
            "time": 1,
            "ticker": 2,
            "company": 3,
            "heading": 4,
            "pages": 5,
            "pdf": 6,
        }

    if column_count >= 5:
        return {
            "date": 0,
            "time": 1,
            "ticker": 2,
            "company": 3,
            "heading": 4,
            "pages": None,
            "pdf": None,
        }

    if column_count >= 4:
        return {
            "date": None,
            "time": 0,
            "ticker": 1,
            "company": 2,
            "heading": 3,
            "pages": None,
            "pdf": None,
        }

    return {
        "date": None,
        "time": None,
        "ticker": None,
        "company": None,
        "heading": None,
        "pages": None,
        "pdf": None,
    }


async def extract_headers(page):
    headers = []
    for cell in await page.query_selector_all(HEADER_SELECTOR):
        headers.append(normalize_header(await cell.inner_text()))
    return headers


async def cell_text(columns, index):
    if index is None or index >= len(columns):
        return None
    text = await columns[index].inner_text()
    cleaned = text.strip()
    return cleaned if cleaned else None


def normalize_key_part(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).lower()


def announcement_key(date, time, ticker, company, heading):
    return (
        normalize_key_part(date),
        normalize_key_part(time),
        normalize_key_part(ticker),
        normalize_key_part(company),
        normalize_key_part(heading),
    )


async def extract_row_primary_link(row, pdf_cell=None):
    candidate_links = []

    search_cells = [pdf_cell] if pdf_cell is not None else []
    for cell in search_cells:
        for anchor in await cell.query_selector_all("a[href]"):
            href = await anchor.get_attribute("href")
            if href:
                candidate_links.append(urljoin(BASE_PAGE, href))

    if not candidate_links:
        for anchor in await row.query_selector_all("a[href]"):
            href = await anchor.get_attribute("href")
            if href:
                candidate_links.append(urljoin(BASE_PAGE, href))

    for link in candidate_links:
        if is_pdf_candidate(link):
            return link

    for link in candidate_links:
        parsed = urlparse(link)
        if parsed.netloc.lower().endswith("marketindex.com.au") and "/announcements/" in parsed.path.lower():
            return link

    return None


async def dismiss_email_popup(page):
    popup = page.locator("#email-only-popup")
    if await popup.count() == 0:
        return False

    close_selectors = [
        "#email-only-popup button:has-text('Close')",
        "#email-only-popup button:has-text('No thanks')",
        "#email-only-popup [aria-label='Close']",
        "#email-only-popup .close",
    ]

    for selector in close_selectors:
        close_button = page.locator(selector)
        if await close_button.count() == 0:
            continue
        try:
            await close_button.first.click(timeout=1000)
            await page.wait_for_timeout(200)
        except Exception:
            pass

    removed = await page.evaluate(
        """
        () => {
            const popup = document.querySelector('#email-only-popup');
            if (!popup) return false;
            popup.remove();
            return true;
        }
        """
    )
    return bool(removed)


async def collect_table_link_lookup(page):
    lookup = {}
    mode = await open_base_page(page)
    print(f"Secondary pass page reload with wait_until='{mode}'.")
    await page.wait_for_selector(ROW_SELECTOR, timeout=30000)

    header_labels = await extract_headers(page)
    header_map = {
        key: find_header_index(header_labels, aliases)
        for key, aliases in HEADER_ALIASES.items()
    }

    while True:
        await page.wait_for_selector(ROW_SELECTOR, timeout=30000)
        rows = await page.query_selector_all(ROW_SELECTOR)

        for row in rows:
            cols = await row.query_selector_all("td")
            if len(cols) < 4:
                continue

            row_map = header_map.copy()
            default_map = default_column_map(len(cols))
            for field in row_map:
                if row_map[field] is None:
                    row_map[field] = default_map[field]

            pdf_idx = row_map["pdf"]
            pdf_cell = cols[pdf_idx] if pdf_idx is not None and pdf_idx < len(cols) else None

            date = await cell_text(cols, row_map["date"])
            time = await cell_text(cols, row_map["time"])
            ticker = await cell_text(cols, row_map["ticker"])
            company = await cell_text(cols, row_map["company"])
            heading = await cell_text(cols, row_map["heading"])

            key = announcement_key(date, time, ticker, company, heading)
            if key in lookup:
                continue

            link = await extract_row_primary_link(row, pdf_cell)
            if link:
                lookup[key] = link

        next_button = page.locator(NEXT_BUTTON_SELECTOR)
        if await next_button.count() == 0:
            break

        classes = await next_button.get_attribute("class") or ""
        if "disabled" in classes.lower():
            break

        await dismiss_email_popup(page)
        try:
            await next_button.click(timeout=10000)
        except Exception:
            await dismiss_email_popup(page)
            await next_button.click(force=True, timeout=10000)

        await page.wait_for_timeout(1500)

    return lookup


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

        target_file.write_bytes(data)
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


async def main():
    parser = argparse.ArgumentParser(description="Download MarketIndex announcement PDFs for parsing.")
    parser.add_argument("--input", default=ANNOUNCEMENTS_FILE, help="Path to marketindex_announcements.json")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Directory to save PDF files")
    parser.add_argument("--report", default=REPORT_FILE, help="Path to JSON download report")
    parser.add_argument("--limit", type=int, default=0, help="Max number of announcements to process (0 = no limit)")
    parser.add_argument("--overwrite", action="store_true", help="Re-download files that already exist")
    parser.add_argument("--headless", action="store_true", help="Run Chromium in headless mode")
    parser.add_argument(
        "--min-download-count",
        type=int,
        default=5,
        help="Quality gate minimum downloaded file count.",
    )
    parser.add_argument(
        "--min-success-ratio",
        type=float,
        default=0.35,
        help="Quality gate minimum success ratio (downloaded / candidate_total).",
    )
    parser.add_argument(
        "--null-retry-delay-seconds",
        type=int,
        default=15,
        help="Seconds to wait before one secondary pass for unresolved announcements.",
    )
    args = parser.parse_args()

    if args.headless:
        print("Headless mode is unsupported for MarketIndex downloads due to anti-bot protections. Re-run without --headless.")
        raise SystemExit(2)

    if args.min_download_count < 0:
        raise ValueError("--min-download-count must be >= 0")
    if not 0 <= args.min_success_ratio <= 1:
        raise ValueError("--min-success-ratio must be between 0 and 1")
    if args.null_retry_delay_seconds < 0:
        raise ValueError("--null-retry-delay-seconds must be >= 0")

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    report_path = Path(args.report)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.loads(input_path.read_text())
    announcements = payload.get("announcements", [])

    if args.limit > 0:
        announcements = announcements[: args.limit]

    results = []
    unresolved_entries = []
    secondary_pass = {
        "attempted": False,
        "unresolved_initial": 0,
        "recovered_links": 0,
        "remaining_unresolved": 0,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context()
        page = await context.new_page()

        mode = await open_base_page(page)
        print(f"Opened base page with wait_until='{mode}'.")

        for idx, announcement in enumerate(announcements, start=1):
            link = announcement.get("link")
            candidate_links = build_candidate_links(announcement)
            announcement_page_url = build_announcement_page_url(announcement)
            if announcement_page_url:
                page_candidates = await extract_pdf_links_from_announcement_page(page, announcement_page_url)
                candidate_links = unique_links(candidate_links + page_candidates)

            record = {
                "index": idx,
                "ticker": announcement.get("ticker"),
                "heading": announcement.get("heading"),
                "link": link,
                "announcement_page_url": announcement_page_url,
                "candidate_links": candidate_links,
            }

            target_file = build_output_path(announcement, idx, output_dir)
            record["file"] = str(target_file)

            if target_file.exists() and not args.overwrite:
                record["status"] = "skipped_exists"
                results.append(record)
                continue

            if not candidate_links:
                record["status"] = "pending_secondary_pass"
                results.append(record)
                unresolved_entries.append(
                    {
                        "record": record,
                        "announcement": announcement,
                        "target_file": target_file,
                    }
                )
                continue

            outcome = await attempt_download_candidate_links(page, candidate_links, target_file)
            record.update(outcome)
            results.append(record)
            if record["status"] == "downloaded":
                print(f"[{idx}] downloaded {target_file.name} ({record['bytes']} bytes)")

        if unresolved_entries:
            secondary_pass["attempted"] = True
            secondary_pass["unresolved_initial"] = len(unresolved_entries)
            print(
                f"Secondary pass: retrying {len(unresolved_entries)} unresolved announcements "
                f"after {args.null_retry_delay_seconds}s delay..."
            )

            if args.null_retry_delay_seconds > 0:
                await asyncio.sleep(args.null_retry_delay_seconds)

            lookup = await collect_table_link_lookup(page)

            remaining = 0
            for entry in unresolved_entries:
                record = entry["record"]
                announcement = entry["announcement"]
                target_file = entry["target_file"]

                key = announcement_key(
                    announcement.get("date"),
                    announcement.get("time"),
                    announcement.get("ticker"),
                    announcement.get("company"),
                    announcement.get("heading"),
                )

                recovered_link = lookup.get(key)
                if recovered_link:
                    secondary_pass["recovered_links"] += 1
                    announcement_with_link = dict(announcement)
                    announcement_with_link["link"] = recovered_link
                    record["link"] = recovered_link
                    record["announcement_page_url"] = build_announcement_page_url(announcement_with_link)

                    candidate_links = build_candidate_links(announcement_with_link)
                    if record["announcement_page_url"]:
                        page_candidates = await extract_pdf_links_from_announcement_page(page, record["announcement_page_url"])
                        candidate_links = unique_links(candidate_links + page_candidates)
                    record["candidate_links"] = candidate_links

                candidate_links = record.get("candidate_links", [])
                if not candidate_links:
                    record["status"] = "skipped_no_candidate_link_after_retry"
                    remaining += 1
                    continue

                outcome = await attempt_download_candidate_links(page, candidate_links, target_file)
                record.update(outcome)
                if record["status"] == "downloaded":
                    print(f"[{record['index']}] downloaded {target_file.name} ({record['bytes']} bytes)")

            secondary_pass["remaining_unresolved"] = remaining
            print(
                f"Secondary pass complete: recovered_links={secondary_pass['recovered_links']} "
                f"remaining_unresolved={secondary_pass['remaining_unresolved']}"
            )

        await browser.close()

    for record in results:
        if record.get("status") == "pending_secondary_pass":
            record["status"] = "skipped_no_candidate_link_after_retry"

    downloaded = sum(1 for record in results if record.get("status") == "downloaded")
    skipped = sum(1 for record in results if str(record.get("status", "")).startswith("skipped"))
    failed = len(results) - downloaded - skipped
    candidate_total = sum(1 for record in results if record.get("candidate_links"))
    success_ratio, quality_gate, gate_failed = evaluate_quality_gate(
        downloaded=downloaded,
        candidate_total=candidate_total,
        min_download_count=args.min_download_count,
        min_success_ratio=args.min_success_ratio,
    )

    report = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "total_processed": len(announcements),
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "candidate_total": candidate_total,
        "success_ratio": success_ratio,
        "quality_gate": quality_gate,
        "secondary_pass": secondary_pass,
        "results": results,
    }

    report_path.write_text(json.dumps(report, indent=2))
    print(
        f"Quality gate: downloaded={downloaded} candidate_total={candidate_total} "
        f"success_ratio={success_ratio:.4f} passed={quality_gate['passed']}"
    )
    print(
        f"Done. downloaded={downloaded} skipped={skipped} failed={failed} "
        f"report={report_path}"
    )

    if gate_failed:
        raise SystemExit(3)


if __name__ == "__main__":
    asyncio.run(main())
