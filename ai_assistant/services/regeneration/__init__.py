"""Servicios para regenerar respuestas IA y conservar versiones."""

from django.db import transaction

from ai_assistant.models import AIMessageVersion, ChatHistory
from ai_assistant.services import ai_service


def ensure_initial_version(message):
    if message.versions.exists():
        return
    AIMessageVersion.objects.create(
        message=message,
        content=message.ai_response or '',
        numero_version=1,
    )


def create_message_with_version(user, user_message, ai_response, document_context=''):
    with transaction.atomic():
        message = ChatHistory.objects.create(
            user=user,
            user_message=user_message,
            ai_response=ai_response,
            document_context=document_context or '',
        )
        AIMessageVersion.objects.create(
            message=message,
            content=ai_response or '',
            numero_version=1,
        )
    return message


def regenerate_message(user, message_id):
    message = ChatHistory.objects.get(pk=message_id, user=user)
    ensure_initial_version(message)
    response = ai_service.chat(
        user,
        message.user_message,
        document_context=message.document_context or '',
    )
    with transaction.atomic():
        last_number = (
            AIMessageVersion.objects
            .select_for_update()
            .filter(message=message)
            .order_by('-numero_version')
            .values_list('numero_version', flat=True)
            .first()
        ) or 0
        version = AIMessageVersion.objects.create(
            message=message,
            content=response or '',
            numero_version=last_number + 1,
        )
        message.ai_response = response or ''
        message.save(update_fields=['ai_response'])
    return message, version


def serialize_versions(message):
    versions = list(message.versions.order_by('numero_version'))
    if not versions and message.ai_response:
        versions = [AIMessageVersion(
            message=message,
            content=message.ai_response,
            numero_version=1,
        )]
    return [
        {
            'id': version.pk,
            'number': version.numero_version,
            'content': version.content,
            'created_at': version.created_at.isoformat() if version.created_at else '',
        }
        for version in versions
    ]
