import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.marketindex.com.au/asx/announcements?page="
OUTPUT_FILE = "data/raw/marketindex_announcements.json"


async def fetch_announcements():
    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context()
        page = await context.new_page()

        all_announcements = []
        page_number = 1

        while True:
            url = BASE_URL + str(page_number)
            print(f"Loading page {page_number}...")
            await page.goto(url, wait_until="networkidle", timeout=90000)

            try:
                await page.wait_for_selector("tbody tr", timeout=30000)
            except:
                print("No rows found, stopping.")
                break

            rows = await page.query_selector_all("tbody tr")

            if not rows:
                print("No more rows.")
                break

            print(f"Found {len(rows)} rows on page {page_number}")

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

            # Stop if fewer than 100 rows (last page)
            if len(rows) < 100:
                break

            page_number += 1

        await browser.close()

        print(f"\nTotal collected: {len(all_announcements)}")

        with open(OUTPUT_FILE, "w") as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "count": len(all_announcements),
                "announcements": all_announcements
            }, f, indent=2)

        print("Saved all announcements.")


if __name__ == "__main__":
    asyncio.run(fetch_announcements())