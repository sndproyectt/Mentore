import requests
import os

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    raise SystemExit("Falta GEMINI_API_KEY en el entorno.")

url = f'https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}'
r = requests.get(url)
models = r.json().get('models', [])
for m in models:
    if 'image' in m['name'].lower() or 'flash' in m['name'].lower():
        print(f"{m['name']} - {m.get('supportedGenerationMethods', [])}")
