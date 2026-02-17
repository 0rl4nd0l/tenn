import asyncio
import json
import re
from collections import defaultdict, deque
from datetime import datetime
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

BASE_URL = "https://www.marketindex.com.au/asx/announcements"
OUTPUT_FILE = "data/raw/marketindex_announcements.json"
FILES_BASE_URL = "https://files.marketindex.com.au/"
API_ANNOUNCEMENTS_MARKER = "data-api.marketindex.com.au/api/v1/announcements"
API_ANNOUNCEMENTS_BASE = "https://data-api.marketindex.com.au/api/v1/announcements"
ROW_SELECTOR = "tbody tr"
HEADER_SELECTOR = "thead th"

HEADER_ALIASES = {
    "date": {"date"},
    "time": {"time"},
    "ticker": {"ticker", "symbol", "code"},
    "company": {"company", "security", "name"},
    "heading": {"heading", "announcement", "title"},
    "pages": {"pages", "page"},
    "pdf": {"pdf", "document", "file"},
}


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


def is_pdf_url(url):
    lower_url = url.lower()
    return lower_url.endswith(".pdf") or ".pdf?" in lower_url


def normalize_key_part(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).lower()


def announcement_key(date, time, ticker, company, heading, pages):
    return (
        normalize_key_part(date),
        normalize_key_part(time),
        normalize_key_part(ticker),
        normalize_key_part(company),
        normalize_key_part(heading),
        normalize_key_part(pages),
    )


def announcement_core_key(date, time, ticker, company, heading):
    return (
        normalize_key_part(date),
        normalize_key_part(time),
        normalize_key_part(ticker),
        normalize_key_part(company),
        normalize_key_part(heading),
    )


def parse_api_datetime_to_table_fields(date_time):
    if not date_time:
        return None, None
    try:
        parsed = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
    except ValueError:
        return None, None
    local_dt = parsed.astimezone(ZoneInfo("Australia/Sydney"))
    date = local_dt.strftime("%d/%m/%y")
    time = local_dt.strftime("%I:%M%p").lstrip("0").lower()
    return date, time


def parse_ticker(symbol_id):
    if not symbol_id:
        return None
    parts = [part for part in str(symbol_id).split(":") if part]
    if not parts:
        return None
    if len(parts) >= 2:
        return parts[1]
    return parts[0]


def build_pdf_url(file_key):
    if not file_key:
        return None
    file_key = str(file_key).strip()
    if not file_key:
        return None
    if file_key.startswith("http://") or file_key.startswith("https://"):
        return file_key
    return urljoin(FILES_BASE_URL, file_key.lstrip("/"))


def slugify_heading(heading):
    if not heading:
        return "announcement"
    slug = heading.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "announcement"


def build_inline_pdf_url(identifier, heading):
    if not identifier:
        return None
    slug = slugify_heading(heading)
    return f"{API_ANNOUNCEMENTS_BASE}/{identifier}/pdf/inline/{slug}"


async def extract_pdf_link(row, pdf_cell=None):
    candidate_links = []

    # Prefer anchors inside the PDF cell.
    search_cells = [pdf_cell] if pdf_cell is not None else []
    for cell in search_cells:
        for anchor in await cell.query_selector_all("a[href]"):
            href = await anchor.get_attribute("href")
            if href:
                candidate_links.append(urljoin(BASE_URL, href))

    # Fallback: scan all links in the row.
    if not candidate_links:
        for anchor in await row.query_selector_all("a[href]"):
            href = await anchor.get_attribute("href")
            if href:
                candidate_links.append(urljoin(BASE_URL, href))

    for link in candidate_links:
        if is_pdf_url(link):
            return link

    return None


async def extract_row_fallback_link(row):
    candidate_links = []
    for anchor in await row.query_selector_all("a[href]"):
        href = await anchor.get_attribute("href")
        if href:
            candidate_links.append(urljoin(BASE_URL, href))

    for link in candidate_links:
        if is_pdf_url(link):
            return link

    for link in candidate_links:
        path = urlparse(link).path.lower()
        if "/asx/" in path and "/announcements/" in path:
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


async def open_announcements_page(page):
    attempts = [
        ("networkidle", 90000),
        ("domcontentloaded", 90000),
        ("load", 90000),
    ]
    last_error = None

    for wait_mode, timeout in attempts:
        try:
            await page.goto(BASE_URL, wait_until=wait_mode, timeout=timeout)
            return wait_mode
        except Exception as error:
            last_error = error
            print(f"Navigation failed with wait_until='{wait_mode}', retrying...")

    raise last_error


async def fetch_announcements():
    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            slow_mo=150,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context()
        page = await context.new_page()
        api_pdf_lookup = defaultdict(deque)
        api_tasks = set()

        async def handle_api_response(response):
            if API_ANNOUNCEMENTS_MARKER not in response.url or response.status != 200:
                return
            try:
                payload = await response.json()
            except Exception:
                return

            announcements = payload.get("data", {}).get("announcements", [])
            for item in announcements:
                inline_pdf_url = build_inline_pdf_url(item.get("identifier"), item.get("heading"))
                file_key_pdf_url = build_pdf_url(item.get("fileKey"))

                pdf_url = inline_pdf_url or file_key_pdf_url
                if not pdf_url:
                    continue
                date, time = parse_api_datetime_to_table_fields(item.get("dateTime"))
                key = announcement_core_key(
                    date,
                    time,
                    parse_ticker(item.get("symbolId")),
                    item.get("securityName"),
                    item.get("heading"),
                )
                api_pdf_lookup[key].append(pdf_url)

        def on_response(response):
            task = asyncio.create_task(handle_api_response(response))
            api_tasks.add(task)
            task.add_done_callback(api_tasks.discard)

        page.on("response", on_response)

        print("Opening page...")
        wait_mode_used = await open_announcements_page(page)
        print(f"Page opened with wait_until='{wait_mode_used}'.")

        await page.wait_for_selector(ROW_SELECTOR, timeout=30000)

        header_labels = await extract_headers(page)
        header_map = {
            key: find_header_index(header_labels, aliases)
            for key, aliases in HEADER_ALIASES.items()
        }

        if any(index is not None for index in header_map.values()):
            print("Detected table columns:", header_labels)
        else:
            print("No reliable headers found; using fallback column positions.")

        all_announcements = []
        page_number = 1

        while True:

            print(f"\nScraping page {page_number}...")
            await page.wait_for_selector(ROW_SELECTOR, timeout=30000)

            rows = await page.query_selector_all(ROW_SELECTOR)
            print(f"Found {len(rows)} rows")
            if api_tasks:
                await asyncio.gather(*list(api_tasks), return_exceptions=True)

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
                key = announcement_core_key(date, time, ticker, company, heading)

                link = None
                if key in api_pdf_lookup and api_pdf_lookup[key]:
                    link = api_pdf_lookup[key].popleft()

                if not link:
                    link = await extract_pdf_link(row, pdf_cell)

                if not link:
                    link = await extract_row_fallback_link(row)

                all_announcements.append({
                    "date": date,
                    "time": time,
                    "ticker": ticker,
                    "company": company,
                    "heading": heading,
                    "link": link
                })

            # Try clicking NEXT button
            next_button = page.locator("div[data-item-id='next']")

            if await next_button.count() == 0:
                print("No next button found. Stopping.")
                break

            # Check if disabled
            classes = await next_button.get_attribute("class") or ""
            if "disabled" in classes.lower():
                print("Next button disabled. Finished pagination.")
                break

            removed_popup = await dismiss_email_popup(page)
            if removed_popup:
                print("Dismissed email popup overlay.")

            print("Clicking next...")
            try:
                await next_button.click(timeout=10000)
            except Exception:
                # Fallback when a transient overlay still intercepts click events.
                await dismiss_email_popup(page)
                await next_button.click(force=True, timeout=10000)

            # Wait for table to refresh
            await page.wait_for_timeout(2000)

            page_number += 1

        await browser.close()

        print(f"\nCollected {len(all_announcements)} announcements.")

        with open(OUTPUT_FILE, "w") as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "count": len(all_announcements),
                "announcements": all_announcements
            }, f, indent=2)

        print("Saved successfully.")


if __name__ == "__main__":
    asyncio.run(fetch_announcements())
