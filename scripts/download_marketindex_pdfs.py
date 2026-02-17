import argparse
import asyncio
import base64
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

ANNOUNCEMENTS_FILE = "data/raw/marketindex_announcements.json"
OUTPUT_DIR = "data/pdfs"
REPORT_FILE = "reports/pdf_download_report.json"
BASE_PAGE = "https://www.marketindex.com.au/asx/announcements"


def sanitize(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip())


def parse_identifier_from_link(link):
    if not link:
        return None
    marker = "/api/v1/announcements/"
    if marker not in link:
        return None
    tail = link.split(marker, 1)[1]
    return tail.split("/", 1)[0] if tail else None


def build_output_path(announcement, index):
    link = announcement.get("link")
    identifier = parse_identifier_from_link(link)

    if identifier:
        name = sanitize(identifier.replace(":", "_"))
    else:
        date = sanitize(announcement.get("date", "unknown-date"))
        time = sanitize((announcement.get("time", "unknown-time")).replace(":", ""))
        ticker = sanitize(announcement.get("ticker", "UNKNOWN"))
        name = f"{date}_{time}_{ticker}_{index:04d}"

    return Path(OUTPUT_DIR) / f"{name}.pdf"


def is_pdf_candidate(link):
    if not link:
        return False
    lower = link.lower()
    return "/pdf/" in lower or lower.endswith(".pdf") or ".pdf?" in lower


async def fetch_pdf_base64(page, url):
    return await page.evaluate(
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
              size: bytes.length,
              base64: btoa(binary),
              head: Array.from(bytes.slice(0, 8))
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
            record = {
                "index": idx,
                "ticker": announcement.get("ticker"),
                "heading": announcement.get("heading"),
                "link": link,
            }

            if not is_pdf_candidate(link):
                record["status"] = "skipped_non_pdf_link"
                results.append(record)
                skipped += 1
                continue

            target_file = build_output_path(announcement, idx)
            record["file"] = str(target_file)

            if target_file.exists() and not args.overwrite:
                record["status"] = "skipped_exists"
                results.append(record)
                skipped += 1
                continue

            fetched = await fetch_pdf_base64(page, link)
            if not fetched.get("ok"):
                record["status"] = "failed_fetch"
                record["http_status"] = fetched.get("status")
                record["content_type"] = fetched.get("contentType")
                record["error"] = fetched.get("error")
                results.append(record)
                failed += 1
                continue

            try:
                data = base64.b64decode(fetched["base64"])
            except Exception as error:
                record["status"] = "failed_decode"
                record["error"] = str(error)
                results.append(record)
                failed += 1
                continue

            if not data.startswith(b"%PDF"):
                record["status"] = "failed_not_pdf"
                record["content_type"] = fetched.get("contentType")
                record["head_bytes"] = list(data[:8])
                results.append(record)
                failed += 1
                continue

            target_file.write_bytes(data)
            record["status"] = "downloaded"
            record["bytes"] = len(data)
            record["content_type"] = fetched.get("contentType")
            results.append(record)
            downloaded += 1
            print(f"[{idx}] downloaded {target_file.name} ({len(data)} bytes)")

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
