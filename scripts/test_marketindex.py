import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

URL = "https://www.marketindex.com.au/asx/announcements"

OUTPUT_FILE = "data/raw/marketindex_announcements.json"


async def fetch_announcements():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("Opening page...")
        await page.goto(URL, timeout=60000)

        # Wait for table to render
        await page.wait_for_selector("table")

        print("Opening items-per-page dropdown...")

        # Click items-per-page control (adjust if text differs)
        try:
            await page.locator("text=Items per page").click()
            await page.wait_for_timeout(1000)
            await page.locator("text=1000").click()
            await page.wait_for_timeout(5000)
        except:
            print("Could not auto-select 1000, continuing with default.")

        print("Extracting rows...")

        rows = await page.query_selector_all("table tbody tr")

        print(f"Found {len(rows)} rows")

        announcements = []

        for row in rows:
            cols = await row.query_selector_all("td")

            if len(cols) < 4:
                continue

            time = await cols[0].inner_text()
            ticker = await cols[1].inner_text()
            company = await cols[2].inner_text()
            heading = await cols[3].inner_text()

            # Extract PDF link
            link_element = await cols[3].query_selector("a")
            link = None

            if link_element:
                href = await link_element.get_attribute("href")
                if href:
                    if href.startswith("http"):
                        link = href
                    else:
                        link = "https://www.marketindex.com.au" + href

            announcements.append({
                "time": time.strip(),
                "ticker": ticker.strip(),
                "company": company.strip(),
                "heading": heading.strip(),
                "link": link
            })

        await browser.close()

        # Save file
        with open(OUTPUT_FILE, "w") as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "count": len(announcements),
                "announcements": announcements
            }, f, indent=2)

        print(f"Saved {len(announcements)} announcements.")


if __name__ == "__main__":
    asyncio.run(fetch_announcements())