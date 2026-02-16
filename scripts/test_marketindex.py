import requests
import os
import json

URL = "https://data-api.marketindex.com.au/api/v1/announcements"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Referer": "https://www.marketindex.com.au/",
    "Origin": "https://www.marketindex.com.au",
    "Accept": "application/json",
}

RAW_DIR = "data/raw"
PROCESSED_FILE = "data/processed_ids.json"

os.makedirs(RAW_DIR, exist_ok=True)

# Load processed IDs
if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, "r") as f:
        processed = set(json.load(f))
else:
    processed = set()

params = {
    "limit": 100,
    "offset": 0,
    "fullTextSearch": "true"
}

response = requests.get(URL, params=params, headers=HEADERS)

data = response.json()
announcements = data["data"]["announcements"]

new_ids = []

for item in announcements:

    identifier = item["identifier"]

    if identifier in processed:
        continue

    filename = identifier.replace(":", "_") + ".txt"
    filepath = os.path.join(RAW_DIR, filename)

    content = f"""
Identifier: {identifier}
Ticker: {item["symbolId"]}
Company: {item["securityName"]}
Heading: {item["heading"]}
DateTime: {item["dateTime"]}
PriceSensitive: {item["isPriceSensitive"]}
PDF: https://data-api.marketindex.com.au/{item["fileKey"]}
"""

    with open(filepath, "w") as f:
        f.write(content.strip())

    print("Saved:", item["heading"])
    new_ids.append(identifier)

processed.update(new_ids)

with open(PROCESSED_FILE, "w") as f:
    json.dump(list(processed), f)

print("Fetch complete.")
