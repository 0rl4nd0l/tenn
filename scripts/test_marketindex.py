import asyncio
import os
from playwright.async_api import async_playwright

SAVE_DIR = "data/raw"
os.makedirs(SAVE_DIR, exist_ok=True)

URL = "https://www.marketindex.com.au/asx-announcements"

async def fetch():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # IMPORTANT
            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        # Remove webdriver flag
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        print("Opening page...")
        await page.goto(URL, timeout=60000)

        await page.wait_for_timeout(8000)

        content = await page.content()

        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(content)

        print("Saved page.")

        await browser.close()

asyncio.run(fetch())