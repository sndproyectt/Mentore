"""Preparacion segura de contexto para comparacion de documentos adjuntos."""
from __future__ import annotations

import logging

from .documents import MAX_API_DOCUMENT_CHARS, truncate_text

logger = logging.getLogger(__name__)

COMPARISON_KEYWORDS = (
    'compara', 'comparar', 'comparacion', 'comparación', 'diferencias',
    'similitudes', 'cambios', 'contrasta', 'faltante', 'aparece en el segundo',
)


def wants_comparison(message):
    text = (message or '').lower()
    return any(keyword in text for keyword in COMPARISON_KEYWORDS)


def build_comparison_context(documents):
    docs = [doc for doc in documents if (doc.extracted_text or '').strip()]
    if len(docs) < 2:
        return '', False

    per_doc_limit = max(1200, MAX_API_DOCUMENT_CHARS // len(docs))
    blocks = []
    truncated_any = False
    for index, doc in enumerate(docs, start=1):
        text, was_cut = truncate_text(
            doc.extracted_text,
            per_doc_limit,
            f'documento {index} ({doc.original_name})',
        )
        truncated_any = truncated_any or was_cut
        blocks.append(
            f'## Documento {index}: {doc.original_name}\n'
            f'Tipo: {doc.file_type or doc.extension}\n'
            f'Contenido extraido:\n{text}'
        )

    instructions = (
        'El usuario quiere comparar los documentos adjuntos. '
        'Analiza unicamente la informacion extraida abajo. '
        'Identifica similitudes, diferencias, informacion faltante, cambios importantes '
        'y conclusiones utiles. Si el contenido no alcanza para comparar, dilo claramente.\n'
    )
    if truncated_any:
        instructions += 'Nota: algunos documentos fueron recortados por limite de tamano.\n'
    return instructions + '\n\n' + '\n\n---\n\n'.join(blocks), truncated_any
