import requests
import os
import json

OLLAMA_URL = "http://localhost:11434/api/generate"

RAW_DIR = "data/raw"
STRUCTURED_DIR = "data/structured"

os.makedirs(STRUCTURED_DIR, exist_ok=True)

def classify(text):

    prompt = f"""
You are a professional equity market analyst.

Your task is to classify an ASX announcement.

Follow these rules strictly:

Relevance Score:
0 = No financial relevance
5 = Moderate relevance
8 = High relevance
10 = Market-moving event

Category must be exactly one of:
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

Impact must be exactly one of:
"High",
"Medium",
"Low"

Confidence rule:
0.5 = Moderate certainty
0.7 = Strong confidence
0.9 = Very strong confidence
1.0 = Extremely confident

Always:
- Provide a confidence between 0.5 and 1.0
- Provide a short one-sentence reason (max 20 words)
- The "reason" field must never be empty

Return ONLY valid JSON.
Do NOT include text outside the JSON.
Do NOT add extra fields.

Announcement:
{text}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }
    )

    return response.json()["response"]


for file in os.listdir(RAW_DIR):

    raw_path = os.path.join(RAW_DIR, file)
    structured_path = os.path.join(STRUCTURED_DIR, file.replace(".txt", ".json"))

    # Skip already classified files
    if os.path.exists(structured_path):
        continue

    with open(raw_path, "r") as f:
        text = f.read()

    print("Classifying:", file)

    result = classify(text)

    # Save JSON
    with open(structured_path, "w") as f:
        f.write(result)

print("Batch classification complete.")
