"""Servicios para registrar feedback humano sobre respuestas IA."""

from ai_assistant.models import AIFeedback, ChatHistory


def set_message_feedback(user, message_id, value):
    value = int(value)
    if value not in (AIFeedback.POSITIVE, AIFeedback.NEGATIVE):
        raise ValueError('Tipo de feedback invalido')

    message = ChatHistory.objects.get(pk=message_id, user=user)
    feedback, _ = AIFeedback.objects.update_or_create(
        usuario=user,
        mensaje=message,
        defaults={'tipo': value},
    )
    return feedback
