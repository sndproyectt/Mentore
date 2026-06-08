import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    raise SystemExit("Falta GEMINI_API_KEY en el entorno.")

url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key={api_key}"
payload = {"instances": [{"prompt": "un gato"}]}
r = requests.post(url, json=payload, timeout=30)
print(f"Status: {r.status_code}")
print(r.text)
