"""
Clase base abstracta para proveedores de IA.
Todos los proveedores deben heredar de esta clase.
"""
import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseProvider(ABC):
    """Interfaz base para proveedores de IA (Groq, Claude, Gemini, etc.)."""

    name = "base"

    def __init__(self, api_key):
        self.api_key = api_key
        if not api_key:
            logger.warning("Proveedor %s inicializado sin API key", self.name)

    def is_configured(self):
        """Verifica si el proveedor tiene una API key válida configurada."""
        return bool(
            self.api_key
            and self.api_key not in ('', 'TU_API_KEY_AQUI')
            and not self.api_key.startswith('TU_API_KEY')
        )

    @abstractmethod
    def chat(self, system_prompt, messages, max_tokens=1500, temperature=0.7):
        """
        Envía una solicitud de chat al proveedor.

        Args:
            system_prompt: Instrucciones del sistema
            messages: Lista de dicts [{"role": "user"|"assistant", "content": "..."}]
            max_tokens: Máximo de tokens en la respuesta
            temperature: Creatividad de la respuesta (0.0 - 1.0)

        Returns:
            str: Texto de respuesta de la IA

        Raises:
            ProviderError: Si ocurre un error en la llamada
        """
        pass

    @abstractmethod
    def chat_stream(self, system_prompt, messages, max_tokens=1500, temperature=0.7):
        """
        Envía una solicitud de chat con streaming al proveedor.

        Args:
            system_prompt: Instrucciones del sistema
            messages: Lista de dicts [{"role": "user"|"assistant", "content": "..."}]
            max_tokens: Máximo de tokens en la respuesta
            temperature: Creatividad de la respuesta (0.0 - 1.0)

        Yields:
            str: Fragmentos de texto conforme se generan

        Raises:
            ProviderError: Si ocurre un error en la llamada
        """
        pass

    def raise_for_http_status(self, response):
        """Convierte HTTP 429 de la API en ProviderRateLimitError."""
        if response.status_code == 429:
            raise ProviderRateLimitError(
                self.name,
                'Límite de solicitudes de la API alcanzado',
                original_error=None,
            )
        response.raise_for_status()


class ProviderError(Exception):
    """Error específico de un proveedor de IA."""

    status_code = None

    def __init__(self, provider_name, message, original_error=None, status_code=None):
        self.provider_name = provider_name
        self.original_error = original_error
        self.status_code = status_code
        super().__init__(f"[{provider_name}] {self._redact_sensitive(message)}")

    @staticmethod
    def _redact_sensitive(message):
        text = str(message)
        text = re.sub(r'([?&]key=)[^&\s]+', r'\1[redacted]', text, flags=re.IGNORECASE)
        text = re.sub(r'(Bearer\s+)[A-Za-z0-9._\-]+', r'\1[redacted]', text, flags=re.IGNORECASE)
        return text


class ProviderRateLimitError(ProviderError):
    """La API del proveedor respondió 429 (demasiadas solicitudes)."""

    status_code = 429
