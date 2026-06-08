"""
Servicio principal de IA para Mentore — Orquestador.

Responsabilidades:
- Seleccionar proveedor de IA (con fallback automático)
- Construir contexto completo (prompt + memoria)
- Ejecutar llamadas sincrónicas y streaming
- Gestionar resúmenes y memoria persistente de forma asíncrona
"""
import logging
from django.conf import settings

from .prompts import build_system_prompt, SUMMARY_PROMPT, MEMORY_EXTRACTION_PROMPT
from .memory import (
    build_full_context,
    should_generate_summary,
    get_messages_for_summary,
    save_summary,
    update_persistent_memory,
)
from .providers.base import ProviderError, ProviderRateLimitError
from .rate_limit import RATE_LIMIT_USER_MESSAGE
from .providers.groq import GroqProvider
from .ai_tools import ai_actions

logger = logging.getLogger(__name__)


def _get_text_providers():
    """
    Retorna los proveedores configurados para chat de texto.
    El chat normal usa Groq; imagenes se generan por image_service.

    Returns:
        list[BaseProvider]: Proveedores configurados y disponibles
    """
    providers = []

    groq_key = getattr(settings, 'GROQ_API_KEY', '')
    groq = GroqProvider(groq_key)
    if groq.is_configured():
        providers.append(groq)

    return providers


def _get_no_provider_message():
    """Mensaje cuando no hay proveedores configurados."""
    return (
        "**API de IA no configurada.**\n\n"
        "Configura la clave de Groq para que el chat responda en texto:\n\n"
        "```\n"
        "GROQ_API_KEY=tu-clave-aqui\n"
        "```"
    )


def _safe_error_for_user(error):
    """Evita mostrar URLs, tokens o API keys en mensajes visibles."""
    if not error:
        return "Error desconocido"
    message = str(error)
    if '413' in message or 'Payload Too Large' in message:
        return 'Payload Too Large'
    status_code = getattr(error, 'status_code', None)
    provider_name = getattr(error, 'provider_name', 'IA')
    if status_code:
        return f'Error del proveedor ({provider_name}, HTTP {status_code})'
    return f'Error del proveedor ({provider_name})'


def _compose_user_message(user_message, document_context=''):
    """Combina mensaje del usuario con texto extraído de documentos adjuntos."""
    if not document_context:
        return user_message
    return f'{document_context}\n\n---\n\n**Pregunta del profesor:**\n{user_message}'


def _build_data_action_response(provider, user, user_message):
    """Detecta y responde preguntas sobre datos reales con herramientas ORM."""
    action = ai_actions.detect_action(provider, user_message)
    if not action:
        return None
    try:
        action_result = ai_actions.execute_action(user, action)
    except Exception:
        logger.exception("Error ejecutando accion IA de solo lectura")
        return "No pude consultar esa informacion del sistema en este momento. Intenta con una pregunta mas especifica."
    messages = ai_actions.build_answer_messages(user_message, action_result)
    return provider.chat(
        ai_actions.ANSWER_PROMPT,
        messages,
        max_tokens=900,
        temperature=0.2,
    )


def chat(user, user_message, document_context=''):
    """
    Procesa un mensaje del usuario de forma sincrónica.
    Construye contexto completo, llama al proveedor con fallback,
    y gestiona memoria en segundo plano.

    Args:
        user: Usuario Django autenticado
        user_message: Texto del mensaje del usuario
        document_context: Texto extraído de documentos adjuntos (opcional)

    Returns:
        str: Respuesta de la IA
    """
    providers = _get_text_providers()
    if not providers:
        return _get_no_provider_message()

    has_docs = bool(document_context and document_context.strip())
    context = build_full_context(user, with_documents=has_docs)
    system_prompt = build_system_prompt(
        user_profile_context=context["user_profile"],
        conversation_summary=context["conversation_summary"],
    )

    full_message = _compose_user_message(user_message, document_context)
    messages = context["messages"] + [{"role": "user", "content": full_message}]

    logger.info(
        "Chat request de %s: %d msgs, doc_chars=%d",
        user.username, len(messages), len(document_context or ''),
    )

    # Intentar con cada proveedor (fallback automático)
    last_error = None
    for provider in providers:
        try:
            logger.info("Intentando con proveedor: %s", provider.name)
            response = _build_data_action_response(provider, user, user_message)
            if response is None:
                response = provider.chat(system_prompt, messages)
            logger.info("Respuesta exitosa de %s", provider.name)

            # Gestionar memoria en background (sin bloquear respuesta)
            _post_response_memory_tasks(user, provider)

            return response

        except ProviderRateLimitError:
            logger.warning("Proveedor %s: límite 429", provider.name)
            raise
        except ProviderError as e:
            logger.warning("Proveedor %s falló: %s", provider.name, str(e))
            last_error = e
            continue

    error_msg = _safe_error_for_user(last_error)
    logger.error("Todos los proveedores fallaron para %s. Último error: %s",
                 user.username, error_msg)
    if isinstance(last_error, ProviderRateLimitError):
        raise ProviderRateLimitError(
            last_error.provider_name,
            RATE_LIMIT_USER_MESSAGE,
        )
    if '413' in error_msg or 'Payload Too Large' in error_msg:
        return (
            "📄 **El documento es demasiado grande** para procesarlo de una vez con la IA.\n\n"
            "Prueba con un PDF más corto, solo las páginas clave, o pregunta por una sección concreta "
            "(por ejemplo: «resume las primeras 5 páginas»).\n\n"
            "_Detalle: el proveedor rechazo el tamano de la solicitud._"
        )
    return (
        "😔 Lo siento, no pude procesar tu solicitud en este momento. "
        "Por favor intenta de nuevo en unos segundos.\n\n"
        f"_Detalle técnico: {error_msg}_"
    )


def _stream_data_action_response(provider, user, user_message):
    """Yield chunks si la pregunta corresponde a una accion ORM; si no, None."""
    action = ai_actions.detect_action(provider, user_message)
    if not action:
        return None
    try:
        action_result = ai_actions.execute_action(user, action)
    except Exception:
        logger.exception("Error ejecutando accion IA de solo lectura en stream")
        return ["No pude consultar esa informacion del sistema en este momento. Intenta con una pregunta mas especifica."]
    messages = ai_actions.build_answer_messages(user_message, action_result)
    return provider.chat_stream(
        ai_actions.ANSWER_PROMPT,
        messages,
        max_tokens=900,
        temperature=0.2,
    )


def chat_stream(user, user_message, document_context=''):
    """
    Procesa un mensaje del usuario con streaming.
    Genera tokens progresivamente para transmisión SSE.

    Args:
        user: Usuario Django autenticado
        user_message: Texto del mensaje del usuario
        document_context: Texto extraído de documentos adjuntos (opcional)

    Yields:
        str: Fragmentos de texto conforme se generan
    """
    providers = _get_text_providers()
    if not providers:
        yield _get_no_provider_message()
        return

    has_docs = bool(document_context and document_context.strip())
    context = build_full_context(user, with_documents=has_docs)
    system_prompt = build_system_prompt(
        user_profile_context=context["user_profile"],
        conversation_summary=context["conversation_summary"],
    )

    full_message = _compose_user_message(user_message, document_context)
    messages = context["messages"] + [{"role": "user", "content": full_message}]

    logger.info(
        "Stream request de %s: %d msgs, doc_chars=%d",
        user.username, len(messages), len(document_context or ''),
    )

    last_error = None
    for provider in providers:
        try:
            logger.info("Stream intentando con: %s", provider.name)
            stream = _stream_data_action_response(provider, user, user_message)
            if stream is None:
                stream = provider.chat_stream(system_prompt, messages)
            for chunk in stream:
                yield chunk

            # Si llegamos aquí, el stream fue exitoso
            logger.info("Stream completado exitosamente con %s", provider.name)
            _post_response_memory_tasks(user, provider)
            return

        except ProviderRateLimitError:
            logger.warning("Stream: proveedor %s límite 429", provider.name)
            raise
        except ProviderError as e:
            logger.warning("Stream: proveedor %s falló: %s", provider.name, str(e))
            last_error = e
            continue

    error_msg = _safe_error_for_user(last_error)
    logger.error("Stream: todos los proveedores fallaron para %s", user.username)
    if isinstance(last_error, ProviderRateLimitError):
        raise ProviderRateLimitError(
            last_error.provider_name,
            RATE_LIMIT_USER_MESSAGE,
        )
    if '413' in error_msg or 'Payload Too Large' in error_msg:
        yield (
            "📄 **El documento es demasiado grande** para la IA en un solo envío. "
            "Prueba con un archivo más corto o pregunta por una parte concreta del PDF."
        )
        return
    yield (
        "😔 Lo siento, no pude procesar tu solicitud. "
        f"Intenta de nuevo. _({error_msg})_"
    )


def _post_response_memory_tasks(user, provider):
    """
    Tareas de memoria post-respuesta:
    1. Verificar si toca generar resumen (medium-term memory)
    2. Extraer información de perfil (persistent memory)

    Estas tareas usan el proveedor más rápido disponible y no bloquean.
    """
    try:
        if should_generate_summary(user):
            _generate_conversation_summary(user, provider)
    except Exception as e:
        logger.error("Error en tareas post-respuesta para %s: %s", user.username, str(e))


def _generate_conversation_summary(user, provider):
    """
    Genera un resumen de los mensajes no resumidos y extrae
    información de perfil del usuario.
    """
    conversation_text, total_messages = get_messages_for_summary(user)

    if not conversation_text.strip():
        return

    logger.info("Generando resumen para %s (%d mensajes totales)", user.username, total_messages)

    try:
        # 1. Generar resumen de conversación
        summary_messages = [{"role": "user", "content": conversation_text}]
        summary = provider.chat(SUMMARY_PROMPT, summary_messages, max_tokens=300, temperature=0.3)

        if summary and not summary.startswith("⚠️"):
            save_summary(user, summary, total_messages)
            logger.info("Resumen generado exitosamente para %s", user.username)

        # 2. Extraer info de perfil
        memory_messages = [{"role": "user", "content": conversation_text}]
        extracted = provider.chat(
            MEMORY_EXTRACTION_PROMPT, memory_messages,
            max_tokens=150, temperature=0.2
        )

        if extracted and not extracted.startswith("⚠️"):
            update_persistent_memory(user, extracted)

    except ProviderError as e:
        logger.warning("No se pudo generar resumen/memoria: %s", str(e))
    except Exception as e:
        logger.error("Error generando resumen para %s: %s", user.username, str(e))
