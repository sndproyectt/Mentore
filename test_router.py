import os

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("HUGGINGFACE_API_KEY", "")
if not api_key:
    raise SystemExit("Falta HUGGINGFACE_API_KEY en el entorno.")

url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
headers = {"Authorization": f"Bearer {api_key}"}
r = requests.post(url, headers=headers, json={"inputs": "un gato"}, timeout=30)
print(r.status_code)
