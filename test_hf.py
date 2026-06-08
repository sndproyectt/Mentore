import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("HUGGINGFACE_API_KEY", "")
if not api_key:
    raise SystemExit("Falta HUGGINGFACE_API_KEY en el entorno.")

url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
headers = {"Authorization": f"Bearer {api_key}"}
payload = {"inputs": "un gato"}
r = requests.post(url, headers=headers, json=payload, timeout=30)
print(f"Status: {r.status_code}")
print(r.headers.get("Content-Type"))
