import requests

url = "https://data-api.marketindex.com.au/api/v1/announcements"

params = {
    "limit": 20,
    "offset": 0,
    "fullTextSearch": "true"
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, params=params, headers=headers)

print(response.status_code)
print(response.json())

