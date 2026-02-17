import requests
import json
from datetime import datetime

BASE_URL = "https://data-api.marketindex.com.au/api/v1/announcements"
OUTPUT_FILE = "data/raw/marketindex_announcements.json"

def fetch_announcements():

    print("Fetching announcements from API...")

    params = {
        "limit": 1000,
        "offset": 0,
        "fullTextSearch": "true"
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.marketindex.com.au/"
    }

    response = requests.get(BASE_URL, params=params, headers=headers)

    if response.status_code != 200:
        print("Error:", response.status_code)
        print(response.text)
        return

    data = response.json()

    announcements = data["data"]["announcements"]

    print(f"Fetched {len(announcements)} announcements.")

    structured = []

    for item in announcements:
        structured.append({
            "time": item.get("dateTime"),
            "ticker": item.get("symbolId"),
            "company": item.get("securityName"),
            "heading": item.get("heading"),
            "file": f"https://files.marketindex.com.au/{item.get('fileKey')}"
        })

    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "fetched_at": datetime.now().isoformat(),
            "count": len(structured),
            "announcements": structured
        }, f, indent=2)

    print("Saved successfully.")


if __name__ == "__main__":
    fetch_announcements()