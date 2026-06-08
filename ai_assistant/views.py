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

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.text import get_valid_filename

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse
from django.templatetags.static import static
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from .models import ChatHistory, ChatDocument, GeneratedDocument, GlobalAssistantPreference
from .services import ai_service
from .services import image_service
from .services import generated_documents
from .services import document_comparison_service
from .services import downloads
from .services import feedback as feedback_service
from .services import regeneration
from .services import speech
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
@xframe_options_sameorigin
def chat_view(request):
    """Vista principal del chat — renderiza la interfaz."""
    history_qs = (
        ChatHistory.objects
        .filter(user=request.user)
        .prefetch_related('versions', 'feedback')
        .order_by('created_at')[:MAX_HISTORY_DISPLAY]
    )
    history = _prepare_history_for_template(history_qs, request.user)
    logger.info("Chat view cargada para %s (%d mensajes)",
                request.user.username, len(history))
    return render(request, 'ai_assistant/chat.html', {'history': history})


@login_required
def global_assistant_preferences(request):
    """Lee o actualiza preferencias del asistente flotante del usuario autenticado."""
    preference, _ = GlobalAssistantPreference.objects.get_or_create(user=request.user)
    if request.method == 'GET':
        return JsonResponse(_serialize_global_assistant_preference(preference))
    if request.method != 'POST':
        return JsonResponse({'error': 'Metodo no permitido'}, status=405)

    try:
        data = json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        data = request.POST

    errors = _update_global_assistant_preference(preference, data)
    if errors:
        return JsonResponse({'errors': errors}, status=400)

    preference.save()
    return JsonResponse(_serialize_global_assistant_preference(preference))


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

    document_context = _get_document_context(request.user, document_ids, user_message)

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
            chat = regeneration.create_message_with_version(
                user=request.user,
                user_message=user_message,
                ai_response=ai_response,
                document_context=document_context,
            )
        except Exception as e:
            logger.error("Error guardando historial: %s", str(e))
            chat = None

        payload = {'response': ai_response}
        if chat:
            payload.update(_serialize_message_actions(chat, request.user))
        generated_doc = _maybe_generate_document(request, user_message, ai_response)
        if generated_doc:
            payload['generated_document'] = generated_doc
        return JsonResponse(payload)
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

    document_context = _get_document_context(request.user, document_ids, user_message)

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

                complete_text = "".join(full_response)
                try:
                    chat = regeneration.create_message_with_version(
                        user=request.user,
                        user_message=user_message,
                        ai_response=complete_text,
                        document_context=document_context,
                    )
                except Exception as e:
                    logger.error("Error guardando historial (stream): %s", str(e))
                    chat = None

                generated_doc = _maybe_generate_document(request, user_message, complete_text)
                if generated_doc:
                    yield f"data: {json.dumps({'generated_document': generated_doc})}\n\n"

                done_payload = {'done': True}
                if chat:
                    done_payload.update(_serialize_message_actions(chat, request.user))
                yield f"data: {json.dumps(done_payload, cls=DjangoJSONEncoder)}\n\n"

            except ProviderRateLimitError:
                yield f"data: {json.dumps({'error': RATE_LIMIT_USER_MESSAGE})}\n\n"
            except Exception as e:
                logger.error("Error en streaming para %s: %s",
                             request.user.username, str(e))
                yield f"data: {json.dumps({'error': 'No se pudo procesar tu solicitud. Intenta de nuevo.'})}\n\n"
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
def download_generated_document(request, pk):
    """Descarga un documento generado por IA, restringido a su usuario."""
    doc = get_object_or_404(GeneratedDocument, user=request.user, pk=pk)
    return FileResponse(
        doc.file.open('rb'),
        as_attachment=True,
        filename=doc.original_name,
    )


@login_required
def message_copy_payload(request, pk):
    """Devuelve contenido validado para copiar una respuesta."""
    message = get_object_or_404(ChatHistory, user=request.user, pk=pk)
    return JsonResponse(downloads.serialize_copy_payload(message))


@login_required
@require_POST
def message_feedback(request, pk):
    """Registra feedback positivo o negativo para una respuesta."""
    message = get_object_or_404(ChatHistory, user=request.user, pk=pk)
    try:
        data = json.loads(request.body or '{}')
    except (json.JSONDecodeError, ValueError):
        data = request.POST
    value = data.get('tipo', data.get('value'))
    try:
        item = feedback_service.set_message_feedback(request.user, message.pk, value)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    return JsonResponse({'ok': True, 'message_id': message.pk, 'feedback': item.tipo})


@login_required
def download_message_response(request, pk):
    """Genera y descarga una respuesta en PDF, TXT o DOCX."""
    message = get_object_or_404(ChatHistory, user=request.user, pk=pk)
    try:
        payload = downloads.build_response_download(
            request.user, message, request.GET.get('format', 'pdf'),
        )
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    response = HttpResponse(payload.content, content_type=payload.content_type)
    response['Content-Disposition'] = f'attachment; filename="{payload.filename}"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@require_POST
def regenerate_message(request, pk):
    """Crea una nueva version de una respuesta IA existente."""
    message = get_object_or_404(ChatHistory, user=request.user, pk=pk)
    try:
        begin_chat_request(request.user)
    except ChatRequestBusy:
        return JsonResponse({'error': BUSY_USER_MESSAGE}, status=409)
    except ChatRateLimited as exc:
        return _rate_limit_response(exc.retry_after)

    try:
        try:
            message, version = regeneration.regenerate_message(request.user, message.pk)
        except ProviderRateLimitError:
            return _rate_limit_response()
        return JsonResponse({
            'ok': True,
            'message_id': message.pk,
            'version': {
                'id': version.pk,
                'number': version.numero_version,
                'content': version.content,
                'created_at': version.created_at,
            },
            'versions': regeneration.serialize_versions(message),
        }, encoder=DjangoJSONEncoder)
    finally:
        release_chat_request(request.user.pk)


@login_required
@require_POST
def message_tts(request, pk):
    """Entrega texto normalizado para lectura por voz de la respuesta."""
    message = get_object_or_404(ChatHistory, user=request.user, pk=pk)
    return JsonResponse(speech.prepare_tts_payload(message))


@login_required
def clear_history(request):
    """Limpia todo el historial de chat del usuario."""
    if request.method == 'POST':
        count = ChatHistory.objects.filter(user=request.user).count()
        ChatHistory.objects.filter(user=request.user).delete()
        logger.info("Historial limpiado para %s (%d mensajes eliminados)",
                     request.user.username, count)
    return redirect('ai_assistant:chat')


@login_required
@require_POST
def generate_image(request):
    """
    Endpoint para generar imágenes usando Gemini API.
    Recibe un prompt de texto y devuelve la imagen generada en base64.
    """
    try:
        data = json.loads(request.body)
        prompt = data.get('prompt', '').strip()
    except (json.JSONDecodeError, ValueError):
        prompt = request.POST.get('prompt', '').strip()

    if not prompt:
        return JsonResponse({'error': 'Escribe una descripción para la imagen'}, status=400)

    if len(prompt) > 1000:
        return JsonResponse({'error': 'La descripción es demasiado larga (máximo 1000 caracteres)'}, status=400)

    if not image_service.is_configured():
        return JsonResponse({
            'error': '⚠️ La generación de imágenes no está configurada. '
                     'Agrega HUGGINGFACE_API_KEY en el archivo .env'
        }, status=503)

    logger.info("Solicitud de imagen de %s: '%s...'", request.user.username, prompt[:50])

    result = image_service.generate_image(prompt, user=request.user)

    if result['success']:
        image_src = f"data:{result['mime_type']};base64,{result['image_data']}"
        text = result.get('text', '')
        ai_response = (
            f"{text}\n\n" if text else ''
        ) + f'<img src="{image_src}" alt="Imagen generada">'
        payload = {
            'image_data': result['image_data'],
            'mime_type': result['mime_type'],
            'text': text,
        }
        try:
            chat = regeneration.create_message_with_version(
                user=request.user,
                user_message=prompt,
                ai_response=ai_response,
            )
            payload.update(_serialize_message_actions(chat, request.user))
        except Exception:
            logger.exception("No se pudo guardar historial de imagen para %s", request.user.username)
        return JsonResponse(payload)
    else:
        return JsonResponse({'error': result['error']}, status=422)


# ============================================================
# HELPERS PRIVADOS
# ============================================================

def _prepare_history_for_template(history, user):
    prepared = []
    for chat in history:
        actions = _serialize_message_actions(chat, user)
        chat.action_versions_json = json.dumps(
            actions['versions'],
            cls=DjangoJSONEncoder,
        )
        chat.action_feedback = actions['feedback']
        chat.action_current_version = actions['current_version']
        prepared.append(chat)
    return prepared


def _global_assistant_avatar_options():
    return [
        {
            'id': 'avatar_a',
            'label': 'Menta',
            'url': static('img/ai/menta.png'),
            'fallback_icon': 'fa-solid fa-graduation-cap',
        },
        {
            'id': 'avatar_b',
            'label': 'Menta transparente',
            'url': static('img/ai/menta_transparent.png'),
            'fallback_icon': 'fa-solid fa-graduation-cap',
        },
    ]


def _serialize_global_assistant_preference(preference):
    avatar_options = _global_assistant_avatar_options()
    avatar = next(
        (item for item in avatar_options if item['id'] == preference.avatar),
        avatar_options[0],
    )
    return {
        'preference': {
            'avatar': preference.avatar,
            'size': preference.size,
            'position': preference.position,
            'transparency': preference.transparency,
            'border_color': preference.border_color,
            'shadow': preference.shadow,
            'animations_enabled': preference.animations_enabled,
            'activity_effect': preference.activity_effect,
            'is_visible': preference.is_visible,
            'drawer_width': preference.drawer_width,
        },
        'selected_avatar': avatar,
        'avatar_options': avatar_options,
        'choices': {
            'avatars': [choice[0] for choice in GlobalAssistantPreference.AVATAR_CHOICES],
            'sizes': [choice[0] for choice in GlobalAssistantPreference.SIZE_CHOICES],
            'positions': [choice[0] for choice in GlobalAssistantPreference.POSITION_CHOICES],
            'border_colors': [choice[0] for choice in GlobalAssistantPreference.BORDER_COLOR_CHOICES],
            'shadows': [choice[0] for choice in GlobalAssistantPreference.SHADOW_CHOICES],
            'activity_effects': [choice[0] for choice in GlobalAssistantPreference.ACTIVITY_EFFECT_CHOICES],
        },
    }


def _update_global_assistant_preference(preference, data):
    errors = {}
    choice_fields = {
        'avatar': GlobalAssistantPreference.AVATAR_CHOICES,
        'size': GlobalAssistantPreference.SIZE_CHOICES,
        'position': GlobalAssistantPreference.POSITION_CHOICES,
        'border_color': GlobalAssistantPreference.BORDER_COLOR_CHOICES,
        'shadow': GlobalAssistantPreference.SHADOW_CHOICES,
        'activity_effect': GlobalAssistantPreference.ACTIVITY_EFFECT_CHOICES,
    }
    for field, choices in choice_fields.items():
        if field not in data:
            continue
        allowed = {choice[0] for choice in choices}
        value = data.get(field)
        if value not in allowed:
            errors[field] = 'Valor no permitido'
        else:
            setattr(preference, field, value)

    if 'transparency' in data:
        try:
            transparency = int(data.get('transparency'))
            if transparency < 0 or transparency > 100:
                raise ValueError
            preference.transparency = transparency
        except (TypeError, ValueError):
            errors['transparency'] = 'Debe estar entre 0 y 100'

    if 'drawer_width' in data:
        try:
            drawer_width = int(data.get('drawer_width'))
            if drawer_width < 320 or drawer_width > 1200:
                raise ValueError
            preference.drawer_width = drawer_width
        except (TypeError, ValueError):
            errors['drawer_width'] = 'Debe estar entre 320 y 1200 pixeles'

    for field in ('animations_enabled', 'is_visible'):
        if field in data:
            value = data.get(field)
            if isinstance(value, bool):
                setattr(preference, field, value)
            elif str(value).lower() in ('true', '1', 'on', 'yes'):
                setattr(preference, field, True)
            elif str(value).lower() in ('false', '0', 'off', 'no'):
                setattr(preference, field, False)
            else:
                errors[field] = 'Debe ser verdadero o falso'
    return errors


def _serialize_message_actions(chat, user):
    feedback_value = 0
    for item in chat.feedback.all():
        if item.usuario_id == user.pk:
            feedback_value = item.tipo
            break
    versions = regeneration.serialize_versions(chat)
    return {
        'message_id': chat.pk,
        'versions': versions,
        'current_version': len(versions) or 1,
        'feedback': feedback_value,
    }

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


def _get_document_context(user, document_ids, user_message=''):
    if not document_ids:
        return ''
    docs = ChatDocument.objects.filter(
        user=user, pk__in=document_ids,
    ).order_by('original_name')
    if document_comparison_service.wants_comparison(user_message):
        context, _ = document_comparison_service.build_comparison_context(docs)
        if context:
            return context
    context, _ = build_documents_context(docs, for_api=True)
    return context


def _maybe_generate_document(request, user_message, ai_response):
    intent = generated_documents.detect_document_intent(user_message)
    if not intent.requested:
        return None
    try:
        doc = generated_documents.generate_document(
            user=request.user,
            file_format=intent.file_format,
            content=ai_response,
            title=intent.title,
            source_prompt=user_message,
        )
        return generated_documents.serialize_generated_document(doc, request=request)
    except Exception:
        logger.exception("No se pudo generar documento descargable para %s", request.user.username)
        return None


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
