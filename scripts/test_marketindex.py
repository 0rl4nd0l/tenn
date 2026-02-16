import asyncio
import json
import math
import re
from datetime import datetime
from playwright.async_api import async_playwright
import requests

# ===== CONFIG =====
BASE_URL = "https://www.marketindex.com.au/asx/announcements?page="
ROWS_PER_PAGE = 100
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"
MIN_RELEVANCE = 7

OUTPUT_ALL = "data/raw/all_announcements.json"
OUTPUT_HIGH = "data/raw/high_priority.json"


# ===== CLASSIFIER =====
def classify(text):

    prompt = f"""
You are a professional equity market analyst.

Classify this ASX announcement.

Relevance Score:
0 = No relevance
5 = Moderate
8 = High
10 = Market-moving

Category must be one of:
"Earnings",
"Guidance",
"Capital Raise",
"M&A",
"Contract",
"Operational Update",
"Director Change",
"Regulatory",
"Trading Halt",
"Other"

Impact must be:
"High", "Medium", or "Low"

Return ONLY valid JSON.

Announcement:
{text}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }
    )

    return json.loads(response.json()["response"])


# ===== SCRAPER =====
async def fetch_announcements():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context()
        page = await context.new_page()

        print("Loading page 1...")
        await page.goto(BASE_URL + "1", wait_until="networkidle", timeout=90000)
        await page.wait_for_selector("tbody tr")

        await page.wait_for_timeout(3000)

        summary_locator = page.locator("text=/Showing.*of.*/")
        summary = await summary_locator.first.inner_text()

        print("Pagination summary:", summary)

        match = re.search(r"of\s+(\d+)", summary)

        if not match:
            print("Could not detect total count.")
            await browser.close()
            return

        total_announcements = int(match.group(1))
        total_pages = math.ceil(total_announcements / ROWS_PER_PAGE)

        print(f"Total announcements: {total_announcements}")
        print(f"Total pages: {total_pages}")

        all_announcements = []
        high_priority = []

        for page_number in range(1, total_pages + 1):

            print(f"\nLoading page {page_number}...")

            if page_number > 1:
                await page.goto(BASE_URL + str(page_number), wait_until="networkidle")
                await page.wait_for_selector("tbody tr")

            rows = await page.query_selector_all("tbody tr")

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
                        link = "https://www.marketindex.com.au" + href

                announcement = {
                    "time": time,
                    "ticker": ticker,
                    "company": company,
                    "heading": heading,
                    "link": link
                }

                # ===== CLASSIFY =====
                try:
                    ai = classify(heading)
                    announcement["ai"] = ai

                    if ai["relevance_score"] >= MIN_RELEVANCE:
                        high_priority.append(announcement)

                except Exception as e:
                    announcement["ai_error"] = str(e)

                all_announcements.append(announcement)

        await browser.close()

        print(f"\nCollected {len(all_announcements)} announcements.")
        print(f"High priority: {len(high_priority)}")

        with open(OUTPUT_ALL, "w") as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "count": len(all_announcements),
                "announcements": all_announcements
            }, f, indent=2)

        with open(OUTPUT_HIGH, "w") as f:
            json.dump({
                "fetched_at": datetime.now().isoformat(),
                "count": len(high_priority),
                "announcements": high_priority
            }, f, indent=2)

        print("Saved successfully.")


if __name__ == "__main__":
    asyncio.run(fetch_announcements())