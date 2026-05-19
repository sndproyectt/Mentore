"""
Sistema de memoria inteligente jerárquica para Mentore IA.

Tres niveles:
1. Short-term: últimos 8 mensajes (coherencia inmediata)
2. Medium-term: resumen automático de la conversación (cada ~10 interacciones)
3. Persistent: perfil pedagógico del usuario (inyectado siempre)
"""
import logging
from django.db.models import Count

logger = logging.getLogger(__name__)

# Configuración de memoria
SHORT_TERM_LIMIT = 8          # Mensajes recientes a incluir
SHORT_TERM_WITH_DOCS = 2    # Menos historial si hay documentos (evita 413)
MAX_MESSAGE_CHARS = 2000    # Recorte por mensaje en historial
SUMMARY_TRIGGER_COUNT = 10    # Cada cuántos mensajes generar resumen
MAX_SUMMARIES_KEPT = 5        # Máximo de resúmenes a mantener por usuario


def _trim_message_content(content):
    """Recorta mensajes largos y quita texto de documentos del historial."""
    if not content:
        return ''
    text = content.strip()
    if '### Archivo:' in text or 'El profesor adjuntó los siguientes documentos' in text:
        if '**Pregunta del profesor:**' in text:
            text = text.split('**Pregunta del profesor:**', 1)[-1].strip()
        else:
            text = '[Consulta con documento adjunto]'
    if len(text) > MAX_MESSAGE_CHARS:
        text = text[:MAX_MESSAGE_CHARS] + '…'
    return text


def get_short_term_memory(user, limit=None):
    """
    Obtiene los últimos N mensajes como memoria a corto plazo.
    Filtra mensajes nulos o corruptos y los ordena cronológicamente (ASC).

    Returns:
        list[dict]: Lista de mensajes [{"role": "user"|"assistant", "content": "..."}]
    """
    from ai_assistant.models import ChatHistory

    msg_limit = limit if limit is not None else SHORT_TERM_LIMIT
    recent = (
        ChatHistory.objects
        .filter(user=user)
        .order_by('-created_at')[:msg_limit]
    )
    # Invertir para orden cronológico ASC
    recent_list = list(recent)[::-1]

    messages = []
    for h in recent_list:
        # Validar que ambos campos sean strings no vacíos
        user_msg = h.user_message if isinstance(h.user_message, str) else ""
        ai_msg = h.ai_response if isinstance(h.ai_response, str) else ""

        user_msg = _trim_message_content(user_msg)
        ai_msg = _trim_message_content(ai_msg)
        if user_msg:
            messages.append({"role": "user", "content": user_msg})
        if ai_msg:
            messages.append({"role": "assistant", "content": ai_msg})

    logger.debug("Short-term memory: %d mensajes para usuario %s", len(messages), user.username)
    return messages


def get_medium_term_memory(user):
    """
    Obtiene el resumen más reciente de la conversación.

    Returns:
        str: Resumen de la conversación o cadena vacía
    """
    from ai_assistant.models import ConversationSummary

    summary = (
        ConversationSummary.objects
        .filter(user=user)
        .order_by('-created_at')
        .first()
    )

    if summary:
        logger.debug("Medium-term memory encontrada: %d chars", len(summary.summary))
        return summary.summary

    return ""


def get_persistent_memory(user):
    """
    Obtiene el perfil pedagógico persistente del usuario.

    Returns:
        str: Contexto del perfil o cadena vacía
    """
    from ai_assistant.models import UserMemory

    try:
        memory = UserMemory.objects.get(user=user)
        profile = memory.get_profile_context()
        if profile:
            logger.debug("Persistent memory encontrada para %s", user.username)
        return profile
    except UserMemory.DoesNotExist:
        return ""


def should_generate_summary(user):
    """
    Determina si es momento de generar un nuevo resumen.
    Se genera cada SUMMARY_TRIGGER_COUNT mensajes no resumidos.

    Returns:
        bool: True si se debe generar resumen
    """
    from ai_assistant.models import ChatHistory, ConversationSummary

    total_messages = ChatHistory.objects.filter(user=user).count()
    last_summary = (
        ConversationSummary.objects
        .filter(user=user)
        .order_by('-created_at')
        .first()
    )

    covered = last_summary.messages_covered if last_summary else 0
    uncovered = total_messages - covered

    return uncovered >= SUMMARY_TRIGGER_COUNT


def get_messages_for_summary(user):
    """
    Obtiene los mensajes no resumidos para generar el próximo resumen.

    Returns:
        tuple: (list[dict], int) — mensajes y total cubierto
    """
    from ai_assistant.models import ChatHistory, ConversationSummary

    total_messages = ChatHistory.objects.filter(user=user).count()
    last_summary = (
        ConversationSummary.objects
        .filter(user=user)
        .order_by('-created_at')
        .first()
    )

    covered = last_summary.messages_covered if last_summary else 0

    # Obtener mensajes después de los ya resumidos
    unsummarized = (
        ChatHistory.objects
        .filter(user=user)
        .order_by('created_at')[covered:total_messages]
    )

    conversation_text = []
    for h in unsummarized:
        if isinstance(h.user_message, str) and h.user_message.strip():
            conversation_text.append(f"Profesor: {h.user_message.strip()}")
        if isinstance(h.ai_response, str) and h.ai_response.strip():
            conversation_text.append(f"Mentore IA: {h.ai_response.strip()}")

    return "\n".join(conversation_text), total_messages


def save_summary(user, summary_text, messages_covered):
    """
    Guarda un nuevo resumen y limpia resúmenes antiguos.
    """
    from ai_assistant.models import ConversationSummary

    ConversationSummary.objects.create(
        user=user,
        summary=summary_text,
        messages_covered=messages_covered,
    )

    # Mantener solo los últimos MAX_SUMMARIES_KEPT resúmenes
    summaries = (
        ConversationSummary.objects
        .filter(user=user)
        .order_by('-created_at')
    )
    old_summaries = summaries[MAX_SUMMARIES_KEPT:]
    if old_summaries.exists():
        old_ids = list(old_summaries.values_list('id', flat=True))
        ConversationSummary.objects.filter(id__in=old_ids).delete()
        logger.info("Eliminados %d resúmenes antiguos para %s", len(old_ids), user.username)

    logger.info("Resumen guardado para %s (%d mensajes cubiertos)", user.username, messages_covered)


def update_persistent_memory(user, extracted_info):
    """
    Actualiza la memoria persistente con información extraída de la conversación.

    Args:
        user: Usuario Django
        extracted_info: Texto con pares clave:valor extraídos por la IA
    """
    from ai_assistant.models import UserMemory

    if not extracted_info or extracted_info.strip() == "SIN_INFO_NUEVA":
        return

    memory, created = UserMemory.objects.get_or_create(user=user)

    # Parsear las líneas de info extraída
    for line in extracted_info.strip().split("\n"):
        line = line.strip()
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if not value:
            continue

        if "grado" in key:
            memory.teaching_grade = value
        elif "materia" in key or "asignatura" in key:
            memory.subjects = value
        elif "estilo" in key:
            memory.teaching_style = value
        elif "actividad" in key:
            memory.preferred_activities = value
        elif "contexto" in key or "escuela" in key or "colegio" in key:
            memory.school_context = value
        else:
            # Agregar a notas adicionales sin duplicar
            if value not in memory.additional_notes:
                separator = "\n" if memory.additional_notes else ""
                memory.additional_notes += f"{separator}{value}"

    memory.save()
    action = "creada" if created else "actualizada"
    logger.info("Memoria persistente %s para %s", action, user.username)


def build_full_context(user, with_documents=False):
    """
    Construye el contexto completo de memoria para una solicitud.

    Returns:
        dict: {
            "messages": [...],           # Short-term messages
            "conversation_summary": "",  # Medium-term summary
            "user_profile": "",          # Persistent profile
        }
    """
    limit = SHORT_TERM_WITH_DOCS if with_documents else SHORT_TERM_LIMIT
    summary = get_medium_term_memory(user)
    if with_documents and len(summary) > 800:
        summary = summary[:800] + '…'

    return {
        "messages": get_short_term_memory(user, limit=limit),
        "conversation_summary": summary,
        "user_profile": get_persistent_memory(user),
    }
