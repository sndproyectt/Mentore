"""
Proveedor Claude (Anthropic) — Fallback para Mentore IA.
"""
import json
import logging
import requests
from .base import BaseProvider, ProviderError, ProviderRateLimitError

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class ClaudeProvider(BaseProvider):
    """Proveedor de IA usando Anthropic Claude."""

    name = "claude"

    def __init__(self, api_key, model=None):
        super().__init__(api_key)
        self.model = model or DEFAULT_MODEL

    def _build_headers(self):
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _build_messages(self, messages):
        """Construye la lista de mensajes en formato Claude."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                formatted.append({"role": role, "content": content.strip()})
        return formatted

    def chat(self, system_prompt, messages, max_tokens=1500, temperature=0.7):
        """Llamada sincrónica a Claude."""
        formatted_messages = self._build_messages(messages)

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": formatted_messages,
        }

        logger.info("Claude request: model=%s, messages=%d", self.model, len(formatted_messages))

        try:
            resp = requests.post(
                CLAUDE_API_URL,
                json=payload,
                headers=self._build_headers(),
                timeout=60,
            )
            self.raise_for_http_status(resp)
            data = resp.json()

            if "content" in data and data["content"]:
                text = data["content"][0].get("text", "").strip()
                if text:
                    logger.info("Claude respuesta exitosa (%d caracteres)", len(text))
                    return text

            logger.error("Claude respuesta inesperada: %s", json.dumps(data)[:500])
            raise ProviderError(self.name, "Respuesta inesperada de Claude")

        except requests.exceptions.Timeout:
            logger.error("Claude timeout")
            raise ProviderError(self.name, "La solicitud tardó demasiado")
        except ProviderRateLimitError:
            raise
        except requests.exceptions.HTTPError as e:
            logger.error("Claude HTTP error: %s", str(e))
            raise ProviderError(self.name, f"Error HTTP: {e}", original_error=e)
        except ProviderError:
            raise
        except Exception as e:
            logger.error("Claude error: %s", str(e))
            raise ProviderError(self.name, f"Error: {str(e)}", original_error=e)

    def chat_stream(self, system_prompt, messages, max_tokens=1500, temperature=0.7):
        """Llamada con streaming a Claude."""
        formatted_messages = self._build_messages(messages)

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": formatted_messages,
            "stream": True,
        }

        logger.info("Claude stream request: model=%s", self.model)

        try:
            resp = requests.post(
                CLAUDE_API_URL,
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
                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type", "")
                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                yield text
                        elif event_type == "message_stop":
                            logger.info("Claude stream completado")
                            return
                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.Timeout:
            logger.error("Claude stream timeout")
            raise ProviderError(self.name, "Streaming tardó demasiado")
        except ProviderRateLimitError:
            raise
        except ProviderError:
            raise
        except Exception as e:
            logger.error("Claude stream error: %s", str(e))
            raise ProviderError(self.name, f"Error en streaming: {str(e)}", original_error=e)
