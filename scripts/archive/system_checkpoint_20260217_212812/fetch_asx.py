import requests
import json
from datetime import datetime

BASE_URL = "https://www.asx.com.au/asx/v2/statistics/announcements"

def fetch_announcements():

    print("Fetching ASX announcements...")

    params = {
        "count": 1000
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    response = requests.get(BASE_URL, params=params, headers=headers)

    if response.status_code != 200:
        print("Error:", response.status_code)
        print(response.text)
        return

    data = response.json()

    announcements = data["data"]

    structured = []

    for item in announcements:
        structured.append({
            "time": item.get("released_at"),
            "ticker": item.get("code"),
            "headline": item.get("headline"),
            "pdf": item.get("url")
        })

    with open("data/raw/asx_announcements.json", "w") as f:
        json.dump({
            "fetched_at": datetime.now().isoformat(),
            "count": len(structured),
            "announcements": structured
        }, f, indent=2)

    print(f"Saved {len(structured)} announcements.")


if __name__ == "__main__":
    fetch_announcements()