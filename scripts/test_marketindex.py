import asyncio
import json
import os
from playwright.async_api import async_playwright

SAVE_DIR = "data/raw"
os.makedirs(SAVE_DIR, exist_ok=True)

URL = "https://www.marketindex.com.au/asx-announcements"

async def fetch_announcements():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        print("Opening page...")
        await page.goto(URL, timeout=60000)

        # Wait for table to appear
        await page.wait_for_selector("table")

        print("Setting items per page to 1000...")

        # Try selecting 1000 items per page
        try:
            await page.select_option("select", value="1000")
            await page.wait_for_timeout(5000)
        except:
            print("Could not auto-select 1000, continuing with default.")

        await page.wait_for_timeout(3000)

        rows = await page.query_selector_all("table tbody tr")

        print(f"Found {len(rows)} rows")

        announcements = []

        for row in rows:

            cols = await row.query_selector_all("td")

            if len(cols) < 4:
                continue

            time_text = await cols[0].inner_text()
            ticker = await cols[1].inner_text()
            company = await cols[2].inner_text()
            heading = await cols[3].inner_text()

            link = None
            link_element = await row.query_selector("a")

            if link_element:
                href = await link_element.get_attribute("href")
                if href:
                    if href.startswith("/"):
                        link = "https://www.marketindex.com.au" + href
                    else:
                        link = href

            announcements.append({
                "time": time_text.strip(),
                "ticker": ticker.strip(),
                "company": company.strip(),
                "heading": heading.strip(),
                "link": link
            })

        output_path = os.path.join(SAVE_DIR, "latest.json")

        with open(output_path, "w") as f:
            json.dump(announcements, f, indent=2)

        print(f"Saved {len(announcements)} announcements.")

        await browser.close()

asyncio.run(fetch_announcements())