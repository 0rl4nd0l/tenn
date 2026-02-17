import asyncio
import json
import math
import re
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.marketindex.com.au/asx/announcements?page="
OUTPUT_FILE = "data/raw/marketindex_announcements.json"
ROWS_PER_PAGE = 100


async def fetch_announcements():
    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        page = await context.new_page()

        print("Loading page 1...")
        await page.goto(BASE_URL + "1", timeout=90000)

        # Give Cloudflare time
        await page.wait_for_timeout(5000)

        await page.wait_for_selector("tbody tr", timeout=60000)

        # Grab pagination summary
        summary_locator = page.locator("text=/Showing.*of.*/")
        summary = await summary_locator.first.inner_text()

        print("Pagination summary:", summary)

        match = re.search(r"of\s+([\d,]+)", summary)

        if not match:
            print("Could not detect total count.")
            await browser.close()
            return

        total_announcements = int(match.group(1).replace(",", ""))
        total_pages = math.ceil(total_announcements / ROWS_PER_PAGE)

        print(f"Total announcements: {total_announcements}")
        print(f"Total pages: {total_pages}")

        all_announcements = []

        for page_number in range(1, total_pages + 1):

            print(f"\nLoading page {page_number}...")

            if page_number > 1:
                await page.goto(BASE_URL + str(page_number), timeout=90000)
                await page.wait_for_timeout(4000)
                await page.wait_for_selector("tbody tr", timeout=60000)

            rows = await page.query_selector_all("tbody tr")
            print(f"Found {len(rows)} rows")

            for row in rows:
                cols = await row.query_selector_all("td")
                if len(cols) < 4:
                    continue

                time = await cols[0].inner_text()
                ticker = await cols[1].inner_text()
                company = await cols[2].inner_text()
                heading_cell = cols[3]
                heading = await heading_cell.inner_text()

                link = None
                link_element = await heading_cell.query_selector("a")
                if link_element:
                    href = await link_element.get_attribute("href")
                    if href:
                        if href.startswith("http"):
                            link = href
                        else:
                            link = "https://www.marketindex.com.au" + href

                all_announcements.append({
                    "time": time.strip(),
                    "ticker": ticker.strip(),
                    "company": company.strip(),
                    "heading": heading.strip(),
                    "link": link
                })

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