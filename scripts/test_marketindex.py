import asyncio
import json
import math
import re
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.marketindex.com.au/asx/announcements?page="
ROWS_PER_PAGE = 100
OUTPUT_FILE = "data/raw/marketindex_announcements.json"


async def fetch_announcements():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = await browser.new_context()
        page = await context.new_page()

        print("Loading page 1...")
        await page.goto(BASE_URL + "1", wait_until="domcontentloaded", timeout=30000)

        await page.wait_for_selector("tbody tr", timeout=30000)

        # Wait for pagination summary to render
        await page.wait_for_timeout(2000)

        # Extract visible pagination text
        summary_locator = page.locator("text=/Showing.*of.*/")

        if await summary_locator.count() == 0:
            print("Could not detect total count.")
            await browser.close()
            return

        summary = await summary_locator.first.inner_text()
        print("Pagination summary:", summary)

        match = re.search(r"of\s+(\d+)", summary)

        if not match:
            print("Regex failed to detect total.")
            await browser.close()
            return

        total_announcements = int(match.group(1))
        total_pages = math.ceil(total_announcements / ROWS_PER_PAGE)

        print(f"Total announcements: {total_announcements}")
        print(f"Total pages: {total_pages}")

        all_announcements = []

        for page_number in range(1, total_pages + 1):

            print(f"\nLoading page {page_number}...")

            if page_number > 1:
                await page.goto(BASE_URL + str(page_number), wait_until="domcontentloaded")
                await page.wait_for_selector("tbody tr", timeout=30000)

            rows = await page.query_selector_all("tbody tr")
            print(f"Found {len(rows)} rows")

            for row in rows:
                cols = await row.query_selector_all("td")
                if len(cols) < 4:
                    continue

                time = (await cols[0].inner_text()).strip()
                ticker = (await cols[1].inner_text()).strip()
                company = (await cols[2].inner_text()).strip()
                heading_cell = cols[3]
                heading = (await heading_cell.inner_text()).strip()

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
                    "time": time,
                    "ticker": ticker,
                    "company": company,
                    "heading": heading,
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