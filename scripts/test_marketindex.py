import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

URL = "https://www.marketindex.com.au/asx/announcements"
OUTPUT_FILE = "data/raw/marketindex_announcements.json"


async def fetch_announcements():
    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,  # IMPORTANT: Avoid Cloudflare detection
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context()
        page = await context.new_page()

        print("Opening page...")
        await page.goto(URL, wait_until="networkidle", timeout=90000)

        print("Waiting for announcement rows...")

        # Wait specifically for rows instead of table
        await page.wait_for_selector("tbody tr", timeout=90000)

        rows = await page.query_selector_all("tbody tr")

        print(f"Found {len(rows)} rows")

        announcements = []

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

            announcements.append({
                "time": time.strip(),
                "ticker": ticker.strip(),
                "company": company.strip(),
                "heading": heading.strip(),
                "link": link
            })

        await browser.close()

        with open(OUTPUT_FILE, "w") as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "count": len(announcements),
                "announcements": announcements
            }, f, indent=2)

        print(f"Saved {len(announcements)} announcements.")


if __name__ == "__main__":
    asyncio.run(fetch_announcements())