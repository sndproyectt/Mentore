"""
Control anti-spam y límites de uso del chat IA (servidor).

Equivalente al patrón «enviando» en el cliente, pero por usuario en Django:
- Una sola solicitud de chat activa por usuario a la vez.
- Cupo de mensajes por minuto para APIs gratuitas con límite RPM.
"""
import time

from django.conf import settings
from django.core.cache import cache

RATE_LIMIT_USER_MESSAGE = (
    'La IA está recibiendo demasiadas solicitudes. Espera unos segundos.'
)
BUSY_USER_MESSAGE = (
    'Ya se está procesando tu mensaje. Espera a que termine.'
)

IN_FLIGHT_KEY = 'ai_chat_inflight:{user_id}'
RATE_BUCKET_KEY = 'ai_chat_rate:{user_id}'

IN_FLIGHT_TTL = getattr(settings, 'AI_CHAT_IN_FLIGHT_TTL', 180)
RATE_WINDOW_SEC = getattr(settings, 'AI_CHAT_RATE_WINDOW_SEC', 60)
MAX_REQUESTS_PER_MINUTE = getattr(settings, 'AI_CHAT_MAX_REQUESTS_PER_MINUTE', 8)


class ChatRequestBusy(Exception):
    """El usuario ya tiene un mensaje de chat en proceso."""


class ChatRateLimited(Exception):
    """Demasiadas solicitudes en la ventana de tiempo."""

    def __init__(self, retry_after=None, message=None):
        self.retry_after = retry_after
        self.message = message or RATE_LIMIT_USER_MESSAGE
        super().__init__(self.message)


def acquire_chat_request(user_id):
    """
    Bloquea una nueva solicitud si ya hay una en curso (enviando = True).
    Raises ChatRequestBusy si no se puede adquirir.
    """
    key = IN_FLIGHT_KEY.format(user_id=user_id)
    if not cache.add(key, 1, timeout=IN_FLIGHT_TTL):
        raise ChatRequestBusy()


def release_chat_request(user_id):
    """Libera el bloqueo al terminar la solicitud (enviando = False)."""
    cache.delete(IN_FLIGHT_KEY.format(user_id=user_id))


def enforce_rate_limit(user_id):
    """
    Incrementa el contador por minuto y rechaza si se supera el cupo.
    Raises ChatRateLimited con segundos sugeridos de espera.
    """
    key = RATE_BUCKET_KEY.format(user_id=user_id)
    now = time.time()
    bucket = cache.get(key)

    if not bucket:
        cache.set(key, {'count': 1, 'start': now}, timeout=RATE_WINDOW_SEC)
        return

    count = bucket.get('count', 0)
    start = bucket.get('start', now)
    elapsed = now - start

    if elapsed >= RATE_WINDOW_SEC:
        cache.set(key, {'count': 1, 'start': now}, timeout=RATE_WINDOW_SEC)
        return

    if count >= MAX_REQUESTS_PER_MINUTE:
        retry_after = max(1, int(RATE_WINDOW_SEC - elapsed))
        raise ChatRateLimited(retry_after=retry_after)

    ttl = max(1, int(RATE_WINDOW_SEC - elapsed))
    cache.set(key, {'count': count + 1, 'start': start}, timeout=ttl)


def begin_chat_request(user):
    """
    Punto de entrada: bloqueo en vuelo + cupo por minuto.
    Llama release_chat_request en finally al terminar.
    """
    user_id = user.pk
    acquire_chat_request(user_id)
    try:
        enforce_rate_limit(user_id)
    except ChatRateLimited:
        release_chat_request(user_id)
        raise
