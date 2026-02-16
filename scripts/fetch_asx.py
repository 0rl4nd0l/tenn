import requests

url = "https://data-api.marketindex.com.au/api/v1/announcements"

params = {
    "limit": 20,
    "offset": 0,
    "fullTextSearch": "true"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Referer": "https://www.marketindex.com.au/",
    "Origin": "https://www.marketindex.com.au",
    "Accept": "application/json",
}

response = requests.get(url, params=params, headers=headers)

print("Status:", response.status_code)
print(response.text[:500])
