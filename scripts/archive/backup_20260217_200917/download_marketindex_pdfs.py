import argparse
import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

ANNOUNCEMENTS_FILE = "data/raw/marketindex_announcements.json"
OUTPUT_DIR = "data/pdfs"
REPORT_FILE = "reports/pdf_download_report.json"
BASE_PAGE = "https://www.marketindex.com.au/asx/announcements"
API_ANNOUNCEMENTS_BASE = "https://data-api.marketindex.com.au/api/v1/announcements"


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


def build_output_path(announcement, index, output_dir):
    link = announcement.get("link")
    identifier = parse_identifier_from_link(link, fallback_ticker=announcement.get("ticker"))

    if identifier:
        name = sanitize(identifier.replace(":", "_"))
    else:
        date = sanitize(announcement.get("date", "unknown-date"))
        time = sanitize((announcement.get("time", "unknown-time")).replace(":", ""))
        ticker = sanitize(announcement.get("ticker", "UNKNOWN"))
        name = f"{date}_{time}_{ticker}_{index:04d}"

    return output_dir / f"{name}.pdf"


def is_pdf_candidate(link):
    if not link:
        return False
    lower = link.lower()
    return "/pdf/" in lower or lower.endswith(".pdf") or ".pdf?" in lower


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


async def fetch_pdf_response(request_context, url):
    try:
        response = await request_context.get(
            url,
            headers={"Accept": "application/pdf,*/*"},
            fail_on_status_code=False,
        )
    except Exception as error:
        return {
            "ok": False,
            "status": 0,
            "contentType": "",
            "error": str(error),
        }

    content_type = response.headers.get("content-type", "")
    if not response.ok:
        try:
            body = await response.text()
        except Exception:
            body = ""
        return {
            "ok": False,
            "status": response.status,
            "contentType": content_type,
            "error": body[:300],
        }

    try:
        data = await response.body()
    except Exception as error:
        return {
            "ok": False,
            "status": response.status,
            "contentType": content_type,
            "error": str(error),
        }

    return {
        "ok": True,
        "status": response.status,
        "contentType": content_type,
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


async def main():
    parser = argparse.ArgumentParser(description="Download MarketIndex announcement PDFs for parsing.")
    parser.add_argument("--input", default=ANNOUNCEMENTS_FILE, help="Path to marketindex_announcements.json")
    parser.add_argument("--output-dir", default=OUTPUT_DIR, help="Directory to save PDF files")
    parser.add_argument("--report", default=REPORT_FILE, help="Path to JSON download report")
    parser.add_argument("--limit", type=int, default=0, help="Max number of announcements to process (0 = no limit)")
    parser.add_argument("--overwrite", action="store_true", help="Re-download files that already exist")
    parser.add_argument("--headless", action="store_true", help="Run Chromium in headless mode")
    args = parser.parse_args()

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
    downloaded = 0
    skipped = 0
    failed = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=args.headless,
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
                skipped += 1
                continue

            if not candidate_links:
                record["status"] = "skipped_no_candidate_link"
                results.append(record)
                skipped += 1
                continue

            fetch_failures = []
            decode_failures = []
            non_pdf_responses = []
            saved = False

            for candidate_link in candidate_links:
                fetched = await fetch_pdf_response(context.request, candidate_link)
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
                record["status"] = "downloaded"
                record["bytes"] = len(data)
                record["content_type"] = fetched.get("contentType")
                record["resolved_link"] = candidate_link
                results.append(record)
                downloaded += 1
                saved = True
                print(f"[{idx}] downloaded {target_file.name} ({len(data)} bytes)")
                break

            if saved:
                continue

            if decode_failures or non_pdf_responses:
                record["status"] = "failed_invalid_pdf_response"
                record["decode_failures"] = decode_failures[:3]
                record["non_pdf_responses"] = non_pdf_responses[:3]
                record["fetch_failures"] = fetch_failures[:3]
                results.append(record)
                failed += 1
                continue

            if fetch_failures:
                record["fetch_failures"] = fetch_failures[:3]
                if all(item.get("http_status") == 404 for item in fetch_failures):
                    # Some announcements appear in the feed before the PDF endpoint is available.
                    record["status"] = "skipped_unavailable"
                    results.append(record)
                    skipped += 1
                else:
                    record["status"] = "failed_fetch"
                    results.append(record)
                    failed += 1
                continue

            record["status"] = "failed_unknown"
            results.append(record)
            failed += 1

        await browser.close()

    report = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "total_processed": len(announcements),
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }

    report_path.write_text(json.dumps(report, indent=2))
    print(
        f"Done. downloaded={downloaded} skipped={skipped} failed={failed} "
        f"report={report_path}"
    )


if __name__ == "__main__":
    asyncio.run(main())
