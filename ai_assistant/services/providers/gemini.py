"""
Proveedor Gemini (Google) — Fallback para Mentore IA.
"""
import json
import logging
import requests
from .base import BaseProvider, ProviderError, ProviderRateLimitError

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1/models"
DEFAULT_MODEL = "gemini-1.5-flash-latest"


class GeminiProvider(BaseProvider):
    """Proveedor de IA usando Google Gemini."""

    name = "gemini"

    def __init__(self, api_key, model=None):
        super().__init__(api_key)
        self.model = model or DEFAULT_MODEL

    def _build_contents(self, messages):
        """Convierte mensajes al formato de Gemini."""
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                gemini_role = "model" if role == "assistant" else "user"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content.strip()}]
                })
        return contents

    def chat(self, system_prompt, messages, max_tokens=1500, temperature=0.7):
        """Llamada sincrónica a Gemini."""
        url = f"{GEMINI_BASE_URL}/{self.model}:generateContent?key={self.api_key}"
        contents = self._build_contents(messages)

        payload = {
            "contents": contents,
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        logger.info("Gemini request: model=%s, contents=%d", self.model, len(contents))

        try:
            resp = requests.post(url, json=payload, timeout=60)
            self.raise_for_http_status(resp)
            data = resp.json()

            if "candidates" in data and data["candidates"]:
                candidate = data["candidates"][0]
                parts = candidate.get("content", {}).get("parts", [])
                if parts:
                    text = parts[0].get("text", "").strip()
                    if text:
                        logger.info("Gemini respuesta exitosa (%d caracteres)", len(text))
                        return text

            logger.error("Gemini respuesta inesperada: %s", json.dumps(data)[:500])
            raise ProviderError(self.name, "Respuesta inesperada de Gemini")

        except requests.exceptions.Timeout:
            logger.error("Gemini timeout")
            raise ProviderError(self.name, "La solicitud tardó demasiado")
        except ProviderRateLimitError:
            raise
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            logger.error("Gemini HTTP error: status=%s", status_code)
            raise ProviderError(
                self.name,
                "Error HTTP del proveedor",
                original_error=e,
                status_code=status_code,
            )
        except ProviderError:
            raise
        except Exception as e:
            logger.error("Gemini error: %s", str(e))
            raise ProviderError(self.name, f"Error: {str(e)}", original_error=e)

    def chat_stream(self, system_prompt, messages, max_tokens=1500, temperature=0.7):
        """Llamada con streaming a Gemini."""
        url = f"{GEMINI_BASE_URL}/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        contents = self._build_contents(messages)

        payload = {
            "contents": contents,
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        logger.info("Gemini stream request: model=%s", self.model)

        try:
            resp = requests.post(url, json=payload, timeout=120, stream=True)
            self.raise_for_http_status(resp)
            resp.encoding = 'utf-8'

            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8', errors='replace')
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                text = parts[0].get("text", "")
                                if text:
                                    yield text
                    except json.JSONDecodeError:
                        continue

            logger.info("Gemini stream completado")

        except requests.exceptions.Timeout:
            logger.error("Gemini stream timeout")
            raise ProviderError(self.name, "Streaming tardó demasiado")
        except ProviderRateLimitError:
            raise
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            logger.error("Gemini stream HTTP error: status=%s", status_code)
            raise ProviderError(
                self.name,
                "Error HTTP del proveedor",
                original_error=e,
                status_code=status_code,
            )
        except ProviderError:
            raise
        except Exception as e:
            logger.error("Gemini stream error: %s", str(e))
            raise ProviderError(self.name, f"Error en streaming: {str(e)}", original_error=e)
