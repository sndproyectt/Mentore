import json
import urllib.parse
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import GoogleCalendarToken

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"
SCOPES = "https://www.googleapis.com/auth/calendar"


def _get_redirect_uri(request):
    return request.build_absolute_uri("/dashboard/calendar/oauth/callback/")


def _refresh_token_if_needed(token_obj):
    """Refresh access token using refresh_token if expired."""
    if not token_obj.refresh_token:
        return False
    now = datetime.now(timezone.utc)
    if token_obj.token_expiry and token_obj.token_expiry > now:
        return True  # still valid

    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": token_obj.refresh_token,
        "grant_type": "refresh_token",
    })
    if resp.status_code == 200:
        data = resp.json()
        token_obj.access_token = data["access_token"]
        if "expires_in" in data:
            from datetime import timedelta
            token_obj.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
        token_obj.save()
        return True
    return False


def _headers(token_obj):
    return {"Authorization": f"Bearer {token_obj.access_token}"}


def _get_token_or_none(user):
    try:
        t = user.google_token
        _refresh_token_if_needed(t)
        return t
    except GoogleCalendarToken.DoesNotExist:
        return None


# ──────────────────────────────────────────────
# VIEWS
# ──────────────────────────────────────────────

@login_required
def schedule_view(request):
    token = _get_token_or_none(request.user)
    connected = token is not None
    return render(request, "calendar_app/schedule.html", {"connected": connected})


@login_required
def oauth_start(request):
    """Redirect user to Google consent screen."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _get_redirect_uri(request),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)
    return redirect(url)


@login_required
def oauth_callback(request):
    """Handle Google OAuth2 callback, exchange code for tokens."""
    code = request.GET.get("code")
    error = request.GET.get("error")

    if error or not code:
        messages.error(request, "No se pudo conectar con Google Calendar.")
        return redirect("calendar_app:schedule")

    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": _get_redirect_uri(request),
        "grant_type": "authorization_code",
    })

    if resp.status_code != 200:
        messages.error(request, "Error al obtener token de Google.")
        return redirect("calendar_app:schedule")

    data = resp.json()
    from datetime import timedelta
    expiry = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))

    GoogleCalendarToken.objects.update_or_create(
        user=request.user,
        defaults={
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "token_expiry": expiry,
        }
    )
    messages.success(request, "¡Google Calendar conectado correctamente!")
    return redirect("calendar_app:schedule")


@login_required
def oauth_disconnect(request):
    try:
        request.user.google_token.delete()
        messages.success(request, "Google Calendar desconectado.")
    except GoogleCalendarToken.DoesNotExist:
        pass
    return redirect("calendar_app:schedule")


# ──────────────────────────────────────────────
# CALENDAR API ENDPOINTS (JSON)
# ──────────────────────────────────────────────

@login_required
def api_events(request):
    """GET: list events. POST: create event."""
    token = _get_token_or_none(request.user)
    if not token:
        return JsonResponse({"error": "not_connected"}, status=401)

    if request.method == "GET":
        time_min = request.GET.get("timeMin", datetime.now(timezone.utc).isoformat())
        time_max = request.GET.get("timeMax", "")
        params = {
            "calendarId": "primary",
            "timeMin": time_min,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 50,
        }
        if time_max:
            params["timeMax"] = time_max

        resp = requests.get(
            f"{GOOGLE_CALENDAR_BASE}/calendars/primary/events",
            headers=_headers(token),
            params=params,
        )
        if resp.status_code == 200:
            return JsonResponse(resp.json())
        return JsonResponse({"error": resp.text}, status=resp.status_code)

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "invalid json"}, status=400)

        event_body = {
            "summary": body.get("summary", ""),
            "description": body.get("description", ""),
            "start": body.get("start"),
            "end": body.get("end"),
            "colorId": body.get("colorId", "1"),
        }
        resp = requests.post(
            f"{GOOGLE_CALENDAR_BASE}/calendars/primary/events",
            headers={**_headers(token), "Content-Type": "application/json"},
            json=event_body,
        )
        if resp.status_code in (200, 201):
            return JsonResponse(resp.json())
        return JsonResponse({"error": resp.text}, status=resp.status_code)

    return JsonResponse({"error": "method not allowed"}, status=405)


@login_required
def api_event_detail(request, event_id):
    """DELETE a specific event."""
    token = _get_token_or_none(request.user)
    if not token:
        return JsonResponse({"error": "not_connected"}, status=401)

    if request.method == "DELETE":
        resp = requests.delete(
            f"{GOOGLE_CALENDAR_BASE}/calendars/primary/events/{event_id}",
            headers=_headers(token),
        )
        if resp.status_code == 204:
            return JsonResponse({"ok": True})
        return JsonResponse({"error": resp.text}, status=resp.status_code)

    return JsonResponse({"error": "method not allowed"}, status=405)
