import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    raise SystemExit("Falta GEMINI_API_KEY en el entorno.")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={api_key}"
payload = {
    "contents": [{"parts": [{"text": "un gato"}]}],
    "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
}
r = requests.post(url, json=payload, timeout=30)
print(f"Status: {r.status_code}")
print(r.text)
