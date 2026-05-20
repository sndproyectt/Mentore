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
import os
import uuid

from django.utils.text import get_valid_filename

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import ChatHistory, ChatDocument
from .services import ai_service
from .services.providers.base import ProviderRateLimitError
from .services.rate_limit import (
    BUSY_USER_MESSAGE,
    RATE_LIMIT_USER_MESSAGE,
    ChatRateLimited,
    ChatRequestBusy,
    begin_chat_request,
    release_chat_request,
)
from .services.documents import (
    ALLOWED_EXTENSIONS,
    EXTENSION_LABELS,
    build_documents_context,
    extract_text_from_file,
    file_icon_class,
    get_extension,
    is_allowed_extension,
)

logger = logging.getLogger(__name__)

# Límites de validación
MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_DISPLAY = 30
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DOCUMENTS_PER_MESSAGE = 5
MAX_DOCUMENTS_LIBRARY = 50


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

    document_ids = _extract_document_ids(request)
    user_message = _ensure_message_or_documents(user_message, document_ids)

    validation_error = _validate_message(user_message)
    if validation_error:
        return JsonResponse({'error': validation_error}, status=400)

    logger.info("send_message de %s: '%s...'",
                request.user.username, user_message[:50])
    doc_error = _validate_document_ids(request.user, document_ids)
    if doc_error:
        return JsonResponse({'error': doc_error}, status=400)

    document_context = _get_document_context(request.user, document_ids)

    try:
        begin_chat_request(request.user)
    except ChatRequestBusy:
        return JsonResponse({'error': BUSY_USER_MESSAGE}, status=409)
    except ChatRateLimited as exc:
        return _rate_limit_response(exc.retry_after)

    try:
        try:
            ai_response = ai_service.chat(
                request.user, user_message, document_context=document_context,
            )
        except ProviderRateLimitError:
            return _rate_limit_response()
        except Exception as e:
            logger.error("Error inesperado en send_message: %s", str(e))
            ai_response = "😔 Ocurrió un error inesperado. Por favor intenta de nuevo."

        try:
            ChatHistory.objects.create(
                user=request.user,
                user_message=user_message,
                ai_response=ai_response,
            )
        except Exception as e:
            logger.error("Error guardando historial: %s", str(e))

        return JsonResponse({'response': ai_response})
    finally:
        release_chat_request(request.user.pk)


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

    document_ids = _extract_document_ids(request)
    user_message = _ensure_message_or_documents(user_message, document_ids)

    validation_error = _validate_message(user_message)
    if validation_error:
        return JsonResponse({'error': validation_error}, status=400)

    logger.info("stream_message de %s: '%s...'",
                request.user.username, user_message[:50])
    doc_error = _validate_document_ids(request.user, document_ids)
    if doc_error:
        return JsonResponse({'error': doc_error}, status=400)

    document_context = _get_document_context(request.user, document_ids)

    try:
        begin_chat_request(request.user)
    except ChatRequestBusy:
        return JsonResponse({'error': BUSY_USER_MESSAGE}, status=409)
    except ChatRateLimited as exc:
        return _rate_limit_response(exc.retry_after)

    user_id = request.user.pk

    def event_stream():
        """Generador SSE que emite chunks de la IA."""
        full_response = []
        try:
            try:
                for chunk in ai_service.chat_stream(
                    request.user, user_message, document_context=document_context,
                ):
                    full_response.append(chunk)
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"

                yield f"data: {json.dumps({'done': True})}\n\n"

                complete_text = "".join(full_response)
                try:
                    ChatHistory.objects.create(
                        user=request.user,
                        user_message=user_message,
                        ai_response=complete_text,
                    )
                except Exception as e:
                    logger.error("Error guardando historial (stream): %s", str(e))

            except ProviderRateLimitError:
                yield f"data: {json.dumps({'error': RATE_LIMIT_USER_MESSAGE})}\n\n"
            except Exception as e:
                logger.error("Error en streaming para %s: %s",
                             request.user.username, str(e))
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            release_chat_request(user_id)

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream; charset=utf-8',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@require_POST
def upload_document(request):
    """Sube un documento, extrae texto y lo guarda en la biblioteca del usuario."""
    try:
        uploaded = request.FILES.get('file')
        if not uploaded:
            return JsonResponse({'error': 'No se recibió ningún archivo'}, status=400)

        if uploaded.size > MAX_DOCUMENT_SIZE:
            return JsonResponse({
                'error': f'El archivo supera el límite de {MAX_DOCUMENT_SIZE // (1024 * 1024)} MB',
            }, status=400)

        if not is_allowed_extension(uploaded.name):
            allowed = ', '.join(sorted(ALLOWED_EXTENSIONS))
            return JsonResponse({
                'error': f'Tipo no permitido. Formatos: {allowed}',
            }, status=400)

        text, extraction_error = extract_text_from_file(uploaded)

        display_name = uploaded.name
        stored_name = f'{uuid.uuid4().hex[:8]}_{get_valid_filename(display_name)}'
        uploaded.name = stored_name

        from django.conf import settings
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

        ext = get_extension(display_name)
        doc = ChatDocument.objects.create(
            user=request.user,
            file=uploaded,
            original_name=display_name,
            file_type=EXTENSION_LABELS.get(ext, ext.lstrip('.').upper()),
            file_size=uploaded.size,
            extracted_text=text if not extraction_error else '',
            extraction_error=extraction_error or '',
        )

        _trim_user_library(request.user)

        if extraction_error:
            return JsonResponse({
                'error': extraction_error,
                'document': _serialize_document(doc),
            }, status=422)

        logger.info('Documento subido: %s por %s', doc.original_name, request.user.username)
        return JsonResponse({'document': _serialize_document(doc)})

    except Exception as e:
        logger.exception('Error subiendo documento para %s', request.user.username)
        hint = (
            '¿Ejecutaste las migraciones? Prueba: python manage.py migrate ai_assistant'
        )
        return JsonResponse({
            'error': f'No se pudo guardar el archivo. {hint}',
            'detail': str(e),
        }, status=500)


@login_required
def list_documents(request):
    """Lista la biblioteca de documentos del usuario (más recientes primero)."""
    docs = ChatDocument.objects.filter(user=request.user)[:MAX_DOCUMENTS_LIBRARY]
    return JsonResponse({
        'documents': [_serialize_document(d) for d in docs],
    })


@login_required
@require_POST
def delete_document(request, pk):
    """Elimina un documento de la biblioteca."""
    doc = ChatDocument.objects.filter(user=request.user, pk=pk).first()
    if not doc:
        return JsonResponse({'error': 'Documento no encontrado'}, status=404)

    if doc.file:
        doc.file.delete(save=False)
    name = doc.original_name
    doc.delete()
    logger.info('Documento eliminado: %s (%s)', name, request.user.username)
    return JsonResponse({'ok': True})


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

def _rate_limit_response(retry_after=None):
    response = JsonResponse(
        {'error': RATE_LIMIT_USER_MESSAGE},
        status=429,
    )
    if retry_after:
        response['Retry-After'] = str(retry_after)
    return response


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


def _extract_document_ids(request):
    try:
        data = json.loads(request.body)
        ids = data.get('document_ids', [])
    except (json.JSONDecodeError, ValueError):
        ids = request.POST.getlist('document_ids')
    if not ids:
        return []
    result = []
    for raw in ids:
        try:
            result.append(int(raw))
        except (TypeError, ValueError):
            continue
    return result


def _validate_document_ids(user, document_ids):
    if len(document_ids) > MAX_DOCUMENTS_PER_MESSAGE:
        return f'Máximo {MAX_DOCUMENTS_PER_MESSAGE} documentos por mensaje'
    if not document_ids:
        return None
    count = ChatDocument.objects.filter(
        user=user, pk__in=document_ids, extraction_error='',
    ).exclude(extracted_text='').count()
    if count != len(set(document_ids)):
        return 'Uno o más documentos no están disponibles o no se pudieron leer'
    return None


def _get_document_context(user, document_ids):
    if not document_ids:
        return ''
    docs = ChatDocument.objects.filter(
        user=user, pk__in=document_ids,
    ).order_by('original_name')
    context, _ = build_documents_context(docs, for_api=True)
    return context


def _trim_user_library(user):
    """Mantiene solo los últimos N documentos por usuario."""
    ids = list(
        ChatDocument.objects.filter(user=user)
        .order_by('-created_at')
        .values_list('pk', flat=True)[MAX_DOCUMENTS_LIBRARY:]
    )
    if not ids:
        return
    for doc in ChatDocument.objects.filter(pk__in=ids):
        if doc.file:
            doc.file.delete(save=False)
        doc.delete()


def _serialize_document(doc):
    ext = doc.extension
    return {
        'id': doc.pk,
        'name': doc.original_name,
        'file_type': doc.file_type,
        'file_size': doc.file_size,
        'size_label': _format_size(doc.file_size),
        'created_at': _format_doc_date(doc.created_at),
        'icon': file_icon_class(ext),
        'ready': doc.is_ready,
        'error': doc.extraction_error or None,
    }


def _format_doc_date(dt):
    months = (
        'ene', 'feb', 'mar', 'abr', 'may', 'jun',
        'jul', 'ago', 'sep', 'oct', 'nov', 'dic',
    )
    hour = dt.hour % 12 or 12
    ampm = 'a.m.' if dt.hour < 12 else 'p.m.'
    minute = dt.strftime('%M')
    return f'{dt.day} {months[dt.month - 1]}, {hour}:{minute} {ampm}'


def _format_size(num_bytes):
    if num_bytes < 1024:
        return f'{num_bytes} B'
    if num_bytes < 1024 * 1024:
        return f'{num_bytes // 1024} KB'
    return f'{num_bytes / (1024 * 1024):.1f} MB'


def _ensure_message_or_documents(message, document_ids):
    if message:
        return message
    if document_ids:
        return (
            'Revisa los documentos adjuntos y explica su contenido de forma clara '
            'y útil para un docente de primaria.'
        )
    return message


def _validate_message(message):
    """
    Valida el mensaje del usuario.
    Returns: str con error o None si es válido.
    """
    if not message:
        return 'Escribe un mensaje o adjunta al menos un documento'
    if len(message) > MAX_MESSAGE_LENGTH:
        return f'El mensaje es demasiado largo (máximo {MAX_MESSAGE_LENGTH} caracteres)'
    return None
