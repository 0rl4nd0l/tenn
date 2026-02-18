import requests
print(requests.post('http://localhost:8000/api/backfill/asx20').text)
