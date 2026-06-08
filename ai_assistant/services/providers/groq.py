"""
Proveedor Groq — Principal proveedor de IA para Mentore.
Usa la API compatible con OpenAI.
"""
import json
import logging
import requests
from .base import BaseProvider, ProviderError, ProviderRateLimitError

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Modelos activos de Groq (actualizados mayo 2026)
GROQ_MODELS = {
    "fast": "llama-3.1-8b-instant",
    "versatile": "llama-3.1-70b-versatile",
}
DEFAULT_MODEL = GROQ_MODELS["fast"]


class GroqProvider(BaseProvider):
    """Proveedor de IA usando Groq Cloud (API compatible OpenAI)."""

    name = "groq"

    def __init__(self, api_key, model=None):
        super().__init__(api_key)
        self.model = model or DEFAULT_MODEL

    def _build_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(self, system_prompt, messages):
        """Construye la lista de mensajes en formato OpenAI."""
        formatted = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                formatted.append({"role": role, "content": content.strip()})
        return formatted

    def chat(self, system_prompt, messages, max_tokens=1500, temperature=0.7):
        """Llamada sincrónica a Groq."""
        formatted_messages = self._build_messages(system_prompt, messages)

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        logger.info("Groq request: model=%s, messages=%d, max_tokens=%d",
                     self.model, len(formatted_messages), max_tokens)

        try:
            resp = requests.post(
                GROQ_API_URL,
                json=payload,
                headers=self._build_headers(),
                timeout=60,
            )
            self.raise_for_http_status(resp)
            data = resp.json()

            if "choices" in data and data["choices"]:
                first = data["choices"][0]
                if "message" in first and "content" in first["message"]:
                    text = first["message"]["content"].strip()
                    logger.info("Groq respuesta exitosa (%d caracteres)", len(text))
                    return text

            logger.error("Groq respuesta inesperada: %s", json.dumps(data)[:500])
            raise ProviderError(self.name, "Respuesta inesperada del modelo")

        except requests.exceptions.Timeout:
            logger.error("Groq timeout después de 60s")
            raise ProviderError(self.name, "La solicitud tardó demasiado. Intenta de nuevo.")
        except ProviderRateLimitError:
            raise
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            logger.error("Groq HTTP error: status=%s - %s", status_code, resp.text[:500] if resp else "")
            raise ProviderError(
                self.name,
                "Error HTTP del proveedor",
                original_error=e,
                status_code=status_code,
            )
        except ProviderError:
            raise
        except Exception as e:
            logger.error("Groq error inesperado: %s", str(e))
            raise ProviderError(self.name, f"Error inesperado: {str(e)}", original_error=e)

    def chat_stream(self, system_prompt, messages, max_tokens=1500, temperature=0.7):
        """Llamada con streaming a Groq (SSE)."""
        formatted_messages = self._build_messages(system_prompt, messages)

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        logger.info("Groq stream request: model=%s, messages=%d",
                     self.model, len(formatted_messages))

        try:
            resp = requests.post(
                GROQ_API_URL,
                json=payload,
                headers=self._build_headers(),
                timeout=120,
                stream=True,
            )
            self.raise_for_http_status(resp)
            resp.encoding = 'utf-8'

            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8', errors='replace')
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        logger.info("Groq stream completado")
                        return
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        logger.warning("Groq stream: línea no parseable: %s", data_str[:100])
                        continue

        except requests.exceptions.Timeout:
            logger.error("Groq stream timeout")
            raise ProviderError(self.name, "Streaming tardó demasiado")
        except ProviderRateLimitError:
            raise
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            logger.error("Groq stream HTTP error: status=%s", status_code)
            raise ProviderError(
                self.name,
                "Error HTTP del proveedor",
                original_error=e,
                status_code=status_code,
            )
        except ProviderError:
            raise
        except Exception as e:
            logger.error("Groq stream error: %s", str(e))
            raise ProviderError(self.name, f"Error en streaming: {str(e)}", original_error=e)
