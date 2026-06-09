"""Interpretacion y ejecucion de acciones internas de IA.

La IA solo puede escoger una accion de esta lista. El backend valida la salida
y ejecuta la consulta real con funciones ORM de data_service.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from . import data_service

logger = logging.getLogger(__name__)


ACTION_NAMES = {
    'list_students',
    'count_students',
    'student_detail',
    'student_grades',
    'student_average',
    'subject_average',
    'top_students',
    'low_average_students',
    'list_classrooms',
    'list_subjects',
    'attendance_summary',
    'count_grades',
}

PARAM_NAMES = {
    'student',
    'subject',
    'grade',
    'classroom',
    'threshold',
    'limit',
    'status',
    'date_from',
    'date_to',
    'activity',
}


@dataclass
class AIAction:
    name: str
    params: dict


ACTION_PROMPT = """
Eres un clasificador de intenciones para un backend Django academico.
Debes responder SOLO JSON valido, sin markdown ni explicaciones.

Si el usuario pregunta por datos reales del sistema (estudiantes, notas,
materias, cursos/grupos, asistencia, conteos o promedios), elige UNA accion.
Si es una conversacion normal, pedagogia general, redaccion, planeacion,
imagenes o documentos, responde {"action":"none","params":{}}.

Acciones permitidas:
- list_students: listar estudiantes. Params: grade, classroom, limit.
- count_students: contar estudiantes. Params: grade, classroom.
- student_detail: datos basicos de un estudiante. Params: student.
- student_grades: notas de estudiante o de una actividad. Params: student, subject, activity, limit.
- student_average: promedio de estudiante. Params: student, subject.
- subject_average: promedio de materia. Params: subject, grade, classroom.
- top_students: estudiantes con promedio mas alto. Params: subject, grade, classroom, limit.
- low_average_students: estudiantes bajo promedio. Params: threshold, subject, grade, classroom, limit.
- list_classrooms: listar cursos/grupos. Params: limit.
- list_subjects: listar materias. Params: limit.
- attendance_summary: resumen de asistencia. Params: student, status, date_from, date_to.
- count_grades: contar notas. Params: student, subject.

Reglas:
- Nunca inventes datos.
- Nunca generes SQL.
- Usa null para parametros ausentes.
- date_from/date_to deben ser YYYY-MM-DD si aparecen.
- threshold debe ser numero. limit debe ser numero.
- Si el usuario menciona una actividad especifica, usa activity con el nombre exacto o frase indicada.

Ejemplo:
Usuario: Cual es la nota de Juan Perez en Matematicas?
Respuesta: {"action":"student_grades","params":{"student":"Juan Perez","subject":"Matematicas","limit":10}}
""".strip()


ANSWER_PROMPT = """
Eres Mentore IA. Responde en espanol natural y breve usando SOLO los datos
consultados por el backend. No muestres JSON ni detalles tecnicos.

Cuando menciones datos concretos recuperados de la base de datos del programa,
resalta cada valor exacto envolviendolo con == y ==. Aplica esto a nombres,
apellidos, correos, notas, grupos, materias, fechas, periodos, cantidades y
otros valores especificos. Ejemplos: ==Jhon Santiago==, ==5.0==,
==pruebita@gmail.com==, ==2B==. No resaltes palabras genericas ni explicaciones.

Si el resultado incluye una lista "grades" con elementos, esas notas SI existen:
responde usando esos registros y no digas que la nota no esta registrada.

Si el backend indica que no encontro informacion, dilo claramente y sugiere
una forma mas precisa de preguntar. Si hay varios estudiantes posibles, pide
al usuario que especifique cual.
""".strip()


def detect_action(provider, user_message):
    """Pide a Groq una accion controlada. Devuelve AIAction o None."""
    try:
        raw = provider.chat(
            ACTION_PROMPT,
            [{'role': 'user', 'content': user_message}],
            max_tokens=350,
            temperature=0.0,
        )
    except Exception as exc:
        logger.warning("No se pudo clasificar accion IA: %s", exc)
        return None

    payload = _parse_json(raw)
    if not payload:
        logger.warning("Clasificador devolvio JSON invalido: %s", raw[:300] if raw else '')
        return None

    action = str(payload.get('action') or '').strip()
    if action == 'none':
        return None
    if action not in ACTION_NAMES:
        logger.warning("Accion IA no permitida: %s", action)
        return None

    params = payload.get('params') or {}
    if not isinstance(params, dict):
        params = {}
    safe_params = {key: params.get(key) for key in PARAM_NAMES if key in params}
    return AIAction(action, safe_params)


def _parse_json(raw):
    if not raw:
        return None
    text = raw.strip()
    if text.startswith('```'):
        text = text.strip('`')
        if text.lower().startswith('json'):
            text = text[4:].strip()
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def execute_action(user, action):
    """Ejecuta una AIAction validada contra funciones ORM de solo lectura."""
    params = action.params
    logger.info("Ejecutando accion IA de solo lectura: %s params=%s", action.name, params)

    if action.name == 'list_students':
        data = data_service.list_students(user, params.get('grade'), params.get('classroom'), params.get('limit'))
    elif action.name == 'count_students':
        data = data_service.count_students(user, params.get('grade'), params.get('classroom'))
    elif action.name == 'student_detail':
        data = data_service.student_detail(user, params.get('student'))
    elif action.name == 'student_grades':
        data = data_service.student_grades(
            user,
            params.get('student'),
            params.get('subject'),
            params.get('limit'),
            params.get('activity'),
        )
    elif action.name == 'student_average':
        data = data_service.student_average(user, params.get('student'), params.get('subject'))
    elif action.name == 'subject_average':
        data = data_service.subject_average(user, params.get('subject'), params.get('grade'), params.get('classroom'))
    elif action.name == 'top_students':
        data = data_service.top_students(user, params.get('subject'), params.get('grade'), params.get('classroom'), params.get('limit'))
    elif action.name == 'low_average_students':
        data = data_service.low_average_students(user, params.get('threshold'), params.get('subject'), params.get('grade'), params.get('classroom'), params.get('limit'))
    elif action.name == 'list_classrooms':
        data = data_service.list_classrooms(user, params.get('limit'))
    elif action.name == 'list_subjects':
        data = data_service.list_subjects(user, params.get('limit'))
    elif action.name == 'attendance_summary':
        data = data_service.attendance_summary(user, params.get('student'), params.get('status'), params.get('date_from'), params.get('date_to'))
    elif action.name == 'count_grades':
        data = data_service.count_grades(user, params.get('student'), params.get('subject'))
    else:
        raise ValueError(f'Accion no soportada: {action.name}')

    return {
        'action': action.name,
        'params': params,
        'result': data,
    }


def build_answer_messages(user_message, action_result):
    """Crea mensajes para que Groq redacte una respuesta conversacional."""
    content = json.dumps(action_result, ensure_ascii=False, default=str)
    return [
        {'role': 'user', 'content': f'Pregunta del usuario: {user_message}\n\nDatos consultados por Django ORM:\n{content}'}
    ]
