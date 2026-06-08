import requests; r = requests.get("https://image.pollinations.ai/prompt/un%20gato?width=1024&height=1024&model=flux&nologo=true", timeout=30); print(r.status_code); print(r.text)
