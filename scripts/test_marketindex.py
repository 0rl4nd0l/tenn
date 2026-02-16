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
            headless=True  # change to False to see browser
        )
        context = await browser.new_context()
        page = await context.new_page()

        print("Opening page...")
        await page.goto(URL, timeout=60000)

        # wait for JS content to load
        await page.wait_for_timeout(5000)

        content = await page.content()

        # Save raw HTML for inspection
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(content)

        print("Page saved to debug_page.html")

        await browser.close()

asyncio.run(fetch_announcements())