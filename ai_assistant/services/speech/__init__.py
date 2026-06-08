"""Servicios de lectura por voz para respuestas IA."""

import re


def prepare_tts_payload(message):
    text = html_to_speech_text(message.ai_response or '')
    return {
        'message_id': message.pk,
        'text': text,
        'lang': 'es-CO',
    }


def html_to_speech_text(content):
    text = content or ''
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', ' imagen generada ', text)
    text = re.sub(r'[`*_#>|-]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
