import json
import requests
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import ChatHistory

SYSTEM_PROMPT = """Eres Mentore IA, un asistente pedagógico especializado en educación primaria colombiana (grados 1° a 5°).

Tu misión es ayudar a los profesores de primaria con:
- Diseño de actividades creativas y lúdicas adaptadas por grado
- Creación de evaluaciones, quizzes, talleres y rúbricas
- Ideas para dinámicas de clase, juegos educativos y proyectos de aula
- Estrategias pedagógicas inclusivas y motivadoras
- Comunicados y mensajes para padres de familia
- Recursos para Matemáticas, Lenguaje, Ciencias, Sociales y Arte

Siempre responde en español colombiano, de manera cálida, práctica y entusiasta.
Adapta el contenido al contexto colombiano cuando sea relevante.
Cuando generes actividades incluye: objetivo, materiales, pasos, duración y evaluación."""


# =========================
# SELECTOR DE IA
# =========================
def call_ai(prompt, history):
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '')
    anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', '')

    if anthropic_key and anthropic_key not in ('TU_API_KEY_DE_ANTHROPIC_AQUI', ''):
        return call_claude(prompt, history, anthropic_key)

    if gemini_key and gemini_key not in ('TU_API_KEY_DE_GEMINI_AQUI', ''):
        return call_gemini(prompt, history, gemini_key)

    return ("⚠️ **API de IA no configurada.**\n\n"
            "Edita `settings.py` y agrega tu clave:\n\n"
            "GEMINI_API_KEY = 'tu-clave'\n"
            "o\n"
            "ANTHROPIC_API_KEY = 'tu-clave'")


# =========================
# CLAUDE (opcional)
# =========================
def call_claude(prompt, history, api_key):
    messages = []

    for h in history.order_by('-created_at')[:6][::-1]:
        messages.append({"role": "user", "content": h.user_message})
        messages.append({"role": "assistant", "content": h.ai_response})

    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1500,
                "system": SYSTEM_PROMPT,
                "messages": messages
            },
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            timeout=30
        )

        resp.raise_for_status()
        data = resp.json()

        if "content" in data and data["content"]:
            return data["content"][0]["text"]

        return "⚠️ Claude no respondió correctamente."

    except Exception as e:
        return f"Error con Claude: {str(e)}"


# =========================
# GEMINI (MEJORADO)
# =========================
def call_gemini(prompt, history, api_key):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-latest:generateContent?key={api_key}"

    contents = []

    # Historial (últimos 6 mensajes, en orden correcto)
    for h in history.order_by('-created_at')[:6][::-1]:
        contents.append({
            "role": "user",
            "parts": [{"text": h.user_message}]
        })
        contents.append({
            "role": "model",
            "parts": [{"text": h.ai_response}]
        })

    # Mensaje actual
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    try:
        resp = requests.post(
            url,
            json={
                "contents": contents,
                "system_instruction": {
                    "parts": [{"text": SYSTEM_PROMPT}]
                },
                "generationConfig": {
                    "temperature": 0.8,
                    "maxOutputTokens": 1500
                }
            },
            timeout=30
        )

        resp.raise_for_status()
        data = resp.json()

        # Validación segura de respuesta
        if "candidates" in data and data["candidates"]:
            return data["candidates"][0]["content"]["parts"][0]["text"]

        return "⚠️ No se pudo generar respuesta con Gemini."

    except Exception as e:
        return f"Error con Gemini: {str(e)}"


# =========================
# VISTAS DJANGO
# =========================

@login_required
def chat_view(request):
    history = ChatHistory.objects.filter(user=request.user).order_by('created_at')[:20]
    return render(request, 'ai_assistant/chat.html', {'history': history})


@login_required
@require_POST
def send_message(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
    except Exception:
        user_message = request.POST.get('message', '').strip()

    # Validaciones
    if not user_message:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)

    if len(user_message) > 1000:
        return JsonResponse({'error': 'Mensaje demasiado largo'}, status=400)

    history = ChatHistory.objects.filter(user=request.user)

    ai_response = call_ai(user_message, history)

    ChatHistory.objects.create(
        user=request.user,
        user_message=user_message,
        ai_response=ai_response
    )

    return JsonResponse({'response': ai_response})


@login_required
def clear_history(request):
    if request.method == 'POST':
        ChatHistory.objects.filter(user=request.user).delete()
    return redirect('ai_assistant:chat')
