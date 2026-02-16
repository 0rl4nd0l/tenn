import requests
import time
import os
import json
from datetime import datetime, timezone, timedelta

# =========================
# CONFIG
# =========================

BASE_URL = "https://data-api.marketindex.com.au/api/v1/announcements"
LIMIT = 100
RATE_DELAY = 3  # seconds between requests
MAX_RETRIES = 3

SAVE_DIR = "data/raw"
os.makedirs(SAVE_DIR, exist_ok=True)

# Browser-like headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.marketindex.com.au/",
    "Connection": "keep-alive"
}


# =========================
# HELPER FUNCTIONS
# =========================

def get_today_range():
    """Return today start and end in ISO format with timezone."""
    now = datetime.now(timezone(timedelta(hours=11)))  # AEST/AEDT adjust if needed
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return start.isoformat(), end.isoformat()


def fetch_announcements():
    start, end = get_today_range()

    params = {
        "limit": LIMIT,
        "offset": 0,
        "fullTextSearch": "true",
        "from": start,
        "to": end
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=10)

            if response.status_code != 200:
                print(f"Blocked or error: {response.status_code}")
                print(response.text[:200])
                time.sleep(5)
                continue

            return response.json()

        except Exception as e:
            print("Fetch error:", e)
            time.sleep(5)

    print("Failed after retries.")
    return None


def save_announcement(item):
    identifier = item.get("identifier")
    heading = item.get("heading", "No Heading")

    safe_filename = identifier.replace(":", "_")
    filepath = os.path.join(SAVE_DIR, f"{safe_filename}.json")

    if os.path.exists(filepath):
        return False  # already saved

    with open(filepath, "w") as f:
        json.dump(item, f, indent=2)

    print(f"Saved: {heading}")
    return True


# =========================
# MAIN
# =========================

def main():
    print("Fetching announcements...")
    data = fetch_announcements()

    if not data:
        return

    announcements = data.get("data", {}).get("announcements", [])

    if not announcements:
        print("No announcements found.")
        return

    saved_count = 0

    for item in announcements:
        if save_announcement(item):
            saved_count += 1
        time.sleep(RATE_DELAY)

    print(f"\nFetch complete. {saved_count} new announcements saved.")


if __name__ == "__main__":
    main()