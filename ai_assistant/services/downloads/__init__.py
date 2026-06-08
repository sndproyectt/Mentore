"""Generacion de descargas para respuestas IA."""

from __future__ import annotations

import mimetypes
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from django.utils import timezone
from django.utils.text import get_valid_filename, slugify

from ai_assistant.models import AIDownloadLog
from ai_assistant.services import generated_documents

TEXT_FORMATS = {'pdf', 'docx', 'txt'}
IMAGE_FORMATS = {'png', 'jpg', 'jpeg'}

CONTENT_TYPES = {
    'pdf': 'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'txt': 'text/plain; charset=utf-8',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
}


@dataclass
class DownloadPayload:
    content: bytes
    content_type: str
    filename: str


def build_response_download(user, message, file_format):
    file_format = (file_format or '').lower().strip()
    if file_format not in TEXT_FORMATS:
        raise ValueError('Formato de descarga no soportado')

    title = _guess_download_title(message)
    content = message.ai_response or ''
    if file_format == 'txt':
        payload = f'{title}\n{"=" * len(title)}\n\n{content.strip()}\n'.encode('utf-8')
    elif file_format == 'docx':
        payload = generated_documents._render_docx(title, content)
    else:
        payload = generated_documents._render_pdf(title, content)

    filename = _filename(title, file_format)
    AIDownloadLog.objects.create(
        usuario=user,
        mensaje=message,
        formato=file_format,
        filename=filename,
    )
    return DownloadPayload(
        content=payload,
        content_type=CONTENT_TYPES[file_format],
        filename=filename,
    )


def image_download_name(image_url, fallback='imagen_generada'):
    parsed = urlparse(image_url or '')
    guessed = mimetypes.guess_type(parsed.path)[0] or ''
    extension = 'jpg' if guessed == 'image/jpeg' else 'png'
    if parsed.path:
        path_name = parsed.path.rsplit('/', 1)[-1]
        if path_name and '.' in path_name:
            return get_valid_filename(path_name)
    return _filename(fallback, extension)


def extract_image_urls(content):
    text = content or ''
    urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', text, flags=re.IGNORECASE)
    urls += re.findall(r'!\[[^\]]*\]\(([^)]+)\)', text)
    return [url for url in urls if url.startswith(('http://', 'https://', 'data:image/'))]


def serialize_copy_payload(message):
    return {
        'id': message.pk,
        'content': message.ai_response or '',
        'image_urls': extract_image_urls(message.ai_response),
    }


def _guess_download_title(message):
    prompt = (message.user_message or '').strip()
    lowered = prompt.lower()
    if 'analisis' in lowered or 'análisis' in lowered or 'compara' in lowered:
        return 'analisis_documento'
    if 'imagen' in lowered:
        return 'imagen_generada'
    words = re.findall(r'[\wáéíóúñÁÉÍÓÚÑ]+', prompt, flags=re.UNICODE)[:5]
    if words:
        return slugify(' '.join(words)) or 'respuesta_ia'
    return 'respuesta_ia'


def _filename(title, file_format):
    base = slugify(title or 'respuesta_ia') or 'respuesta_ia'
    timestamp = timezone.localtime().strftime('%Y%m%d_%H%M')
    return get_valid_filename(f'{base}_{timestamp}.{file_format}')
