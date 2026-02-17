import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "https://www.marketindex.com.au/asx/announcements"
OUTPUT_FILE = "data/raw/marketindex_announcements.json"


async def fetch_announcements():
    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            slow_mo=150,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context()
        page = await context.new_page()

        print("Opening page...")
        await page.goto(BASE_URL, wait_until="networkidle", timeout=90000)

        await page.wait_for_selector("tbody tr", timeout=30000)

        all_announcements = []
        page_number = 1

        while True:

            print(f"\nScraping page {page_number}...")
            await page.wait_for_selector("tbody tr", timeout=30000)

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

            # Try clicking NEXT button
            next_button = page.locator("div[data-item-id='next']")

            if await next_button.count() == 0:
                print("No next button found. Stopping.")
                break

            # Check if disabled
            classes = await next_button.get_attribute("class")
            if "disabled" in classes.lower():
                print("Next button disabled. Finished pagination.")
                break

            print("Clicking next...")
            await next_button.click()

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