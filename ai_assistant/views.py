"""
Vistas de Django para el módulo de Asistente IA.

Responsabilidades EXCLUSIVAS:
- Manejo de HTTP requests/responses
- Validación básica de entrada
- Autenticación de usuario
- Persistencia en base de datos
- NO contiene lógica de IA (delegada a services/)
"""
import json
import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import ChatHistory
from .services import ai_service

logger = logging.getLogger(__name__)

# Límites de validación
MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_DISPLAY = 30


@login_required
def chat_view(request):
    """Vista principal del chat — renderiza la interfaz."""
    history = (
        ChatHistory.objects
        .filter(user=request.user)
        .order_by('created_at')[:MAX_HISTORY_DISPLAY]
    )
    logger.info("Chat view cargada para %s (%d mensajes)",
                request.user.username, history.count() if hasattr(history, 'count') else len(history))
    return render(request, 'ai_assistant/chat.html', {'history': history})


@login_required
@require_POST
def send_message(request):
    """
    Endpoint sincrónico: recibe mensaje, llama a la IA y devuelve respuesta JSON.
    Usado como fallback cuando el streaming no está disponible.
    """
    # Parsear input
    user_message = _extract_message(request)
    if user_message is None:
        return JsonResponse({'error': 'No se pudo leer el mensaje'}, status=400)

    # Validar
    validation_error = _validate_message(user_message)
    if validation_error:
        return JsonResponse({'error': validation_error}, status=400)

    logger.info("send_message de %s: '%s...'",
                request.user.username, user_message[:50])

    # Delegar a servicio de IA
    try:
        ai_response = ai_service.chat(request.user, user_message)
    except Exception as e:
        logger.error("Error inesperado en send_message: %s", str(e))
        ai_response = "😔 Ocurrió un error inesperado. Por favor intenta de nuevo."

    # Persistir en base de datos
    try:
        ChatHistory.objects.create(
            user=request.user,
            user_message=user_message,
            ai_response=ai_response,
        )
    except Exception as e:
        logger.error("Error guardando historial: %s", str(e))

    return JsonResponse({'response': ai_response})


@login_required
@require_POST
def stream_message(request):
    """
    Endpoint de streaming SSE: transmite tokens progresivamente.
    El frontend se conecta con EventSource para renderizado incremental.
    """
    # Parsear input
    user_message = _extract_message(request)
    if user_message is None:
        return JsonResponse({'error': 'No se pudo leer el mensaje'}, status=400)

    # Validar
    validation_error = _validate_message(user_message)
    if validation_error:
        return JsonResponse({'error': validation_error}, status=400)

    logger.info("stream_message de %s: '%s...'",
                request.user.username, user_message[:50])

    def event_stream():
        """Generador SSE que emite chunks de la IA."""
        full_response = []
        try:
            for chunk in ai_service.chat_stream(request.user, user_message):
                full_response.append(chunk)
                # Formato SSE: data: <contenido>\n\n
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # Señal de fin
            yield f"data: {json.dumps({'done': True})}\n\n"

            # Persistir respuesta completa
            complete_text = "".join(full_response)
            try:
                ChatHistory.objects.create(
                    user=request.user,
                    user_message=user_message,
                    ai_response=complete_text,
                )
            except Exception as e:
                logger.error("Error guardando historial (stream): %s", str(e))

        except Exception as e:
            logger.error("Error en streaming para %s: %s",
                         request.user.username, str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream; charset=utf-8',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
def clear_history(request):
    """Limpia todo el historial de chat del usuario."""
    if request.method == 'POST':
        count = ChatHistory.objects.filter(user=request.user).count()
        ChatHistory.objects.filter(user=request.user).delete()
        logger.info("Historial limpiado para %s (%d mensajes eliminados)",
                     request.user.username, count)
    return redirect('ai_assistant:chat')


# ============================================================
# HELPERS PRIVADOS
# ============================================================

def _extract_message(request):
    """Extrae el mensaje del request (JSON o form-data)."""
    try:
        data = json.loads(request.body)
        return data.get('message', '').strip()
    except (json.JSONDecodeError, ValueError):
        return request.POST.get('message', '').strip()
    except Exception as e:
        logger.error("Error extrayendo mensaje: %s", str(e))
        return None


def _validate_message(message):
    """
    Valida el mensaje del usuario.
    Returns: str con error o None si es válido.
    """
    if not message:
        return 'El mensaje está vacío'
    if len(message) > MAX_MESSAGE_LENGTH:
        return f'El mensaje es demasiado largo (máximo {MAX_MESSAGE_LENGTH} caracteres)'
    return None
