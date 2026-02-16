import asyncio
import json
import math
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.marketindex.com.au/asx/announcements"
OUTPUT_FILE = "data/raw/marketindex_announcements.json"
ITEMS_PER_PAGE = 100


async def fetch_announcements():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Opening page 1...")
        await page.goto(f"{BASE_URL}?page=1")

        # Wait for page content (NOT networkidle)
        await page.wait_for_timeout(5000)

        # Detect total announcements from pagination summary
        summary = await page.locator("text=Showing").first.inner_text()
        print("Pagination summary:", summary)

        import re
        match = re.search(r"of\s+([\d,]+)", summary)

        if not match:
            print("Could not detect total count.")
            await browser.close()
            return

        total_announcements = int(match.group(1).replace(",", ""))
        total_pages = math.ceil(total_announcements / ITEMS_PER_PAGE)

        print("Total announcements:", total_announcements)
        print("Total pages:", total_pages)

        all_data = []

        for page_number in range(1, total_pages + 1):
            print(f"\nLoading page {page_number}...")
            await page.goto(f"{BASE_URL}?page={page_number}")
            await page.wait_for_timeout(4000)

            rows = await page.locator("tbody tr").all()
            print("Found", len(rows), "rows")

            for row in rows:
                cells = await row.locator("td").all()

                if len(cells) < 4:
                    continue

                time_text = await cells[0].inner_text()
                ticker = await cells[1].inner_text()
                headline = await cells[2].inner_text()

                link_element = cells[2].locator("a")
                link = await link_element.get_attribute("href")

                if link:
                    link = "https://www.marketindex.com.au" + link

                all_data.append({
                    "time": time_text.strip(),
                    "ticker": ticker.strip(),
                    "headline": headline.strip(),
                    "link": link
                })

        with open(OUTPUT_FILE, "w") as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "count": len(all_data),
                "announcements": all_data
            }, f, indent=2)

        print("\nCollected", len(all_data), "announcements.")
        print("Saved successfully.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(fetch_announcements())