import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RegisterForm, LoginForm, ProfileForm
from .models import TeacherProfile, SocialAccount

User = get_user_model()

# ── OAuth2 constants ──────────────────────────────────────────
GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPE     = "openid email profile https://www.googleapis.com/auth/gmail.send"

APPLE_AUTH_URL   = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL  = "https://appleid.apple.com/auth/token"


def _google_redirect_uri(request):
    return request.build_absolute_uri("/accounts/social/google/callback/")

def _apple_redirect_uri(request):
    return request.build_absolute_uri("/accounts/social/apple/callback/")


def _get_or_create_social_user(provider, provider_id, email, full_name, avatar_url):
    """Find or create a Django User from a social login."""
    # 1. Already linked?
    try:
        sa = SocialAccount.objects.get(provider=provider, provider_id=provider_id)
        return sa.user
    except SocialAccount.DoesNotExist:
        pass

    # 2. User with same email?
    user = None
    if email:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            pass

    # 3. Create new user
    if user is None:
        base_username = (email.split("@")[0] if email else provider_id)[:28]
        username = base_username
        n = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{n}"
            n += 1
        parts = (full_name or "").strip().split(" ", 1)
        user = User.objects.create_user(
            username=username,
            email=email or "",
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else "",
        )
        user.set_unusable_password()
        user.save()

    # 4. Link social account
    SocialAccount.objects.update_or_create(
        provider=provider, provider_id=provider_id,
        defaults={"user": user, "email": email or "", "avatar_url": avatar_url or ""},
    )

    # 5. Ensure TeacherProfile
    TeacherProfile.objects.get_or_create(user=user)
    return user


# ── Standard auth views ───────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('students:dashboard')
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'¡Bienvenido a Mentore, {user.first_name}!')
            return redirect('students:dashboard')
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('students:dashboard')
    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('students:dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
    form = ProfileForm(instance=profile, initial={
        'first_name': request.user.first_name,
        'last_name':  request.user.last_name,
        'email':      request.user.email,
    })
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name  = form.cleaned_data.get('last_name', '')
            request.user.email      = form.cleaned_data.get('email', '')
            request.user.save()
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('accounts:profile')
    social = request.user.social_accounts.all()
    return render(request, 'accounts/profile.html', {'form': form, 'profile': profile, 'social_accounts': social})


# ── GOOGLE OAuth2 ─────────────────────────────────────────────

def google_login(request):
    if not getattr(settings, 'GOOGLE_CLIENT_ID', ''):
        messages.error(request, 'Google login no está configurado. Agrega GOOGLE_CLIENT_ID en settings.py')
        return redirect('accounts:login')
    params = {
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "redirect_uri":  _google_redirect_uri(request),
        "response_type": "code",
        "scope":         GOOGLE_SCOPE,
        "access_type":   "offline",
        "prompt":        "consent",   # fuerza refresh_token siempre
    }
    return redirect(GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params))


def google_callback(request):
    code  = request.GET.get("code")
    error = request.GET.get("error")

    if error or not code:
        messages.error(request, "No se pudo iniciar sesión con Google.")
        return redirect('accounts:login')

    # Exchange code → tokens
    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "code":          code,
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri":  _google_redirect_uri(request),
        "grant_type":    "authorization_code",
    })
    if resp.status_code != 200:
        messages.error(request, "Error al obtener token de Google.")
        return redirect('accounts:login')

    token_data   = resp.json()
    access_token = token_data.get("access_token")

    # Get user info
    info_resp = requests.get(GOOGLE_USERINFO, headers={"Authorization": f"Bearer {access_token}"})
    if info_resp.status_code != 200:
        messages.error(request, "No se pudo obtener información de tu cuenta Google.")
        return redirect('accounts:login')

    info = info_resp.json()
    user = _get_or_create_social_user(
        provider    = "google",
        provider_id = info.get("sub"),
        email       = info.get("email", ""),
        full_name   = info.get("name", ""),
        avatar_url  = info.get("picture", ""),
    )

    # ── Save / update OAuth tokens ───────────────────────────
    from django.utils import timezone as _tz
    refresh_token = token_data.get("refresh_token", "")
    expires_in    = token_data.get("expires_in", 3600)

    social_qs = user.social_accounts.filter(provider="google")
    if social_qs.exists():
        social = social_qs.first()
        social.access_token = access_token
        social.token_expiry = _tz.now() + _tz.timedelta(seconds=expires_in)
        # refresh_token only comes on first consent or after prompt=consent
        if refresh_token:
            social.refresh_token = refresh_token
        social.save(update_fields=["access_token", "token_expiry", "refresh_token"])

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, f"¡Bienvenido, {user.first_name or user.username}! Sesión iniciada con Google.")
    return redirect('students:dashboard')


# ── APPLE OAuth2 ──────────────────────────────────────────────

def apple_login(request):
    if not getattr(settings, 'APPLE_CLIENT_ID', ''):
        messages.error(request, 'Apple login no está configurado. Agrega APPLE_CLIENT_ID en settings.py')
        return redirect('accounts:login')
    params = {
        "client_id":     settings.APPLE_CLIENT_ID,
        "redirect_uri":  _apple_redirect_uri(request),
        "response_type": "code",
        "response_mode": "form_post",
        "scope":         "name email",
    }
    return redirect(APPLE_AUTH_URL + "?" + urllib.parse.urlencode(params))


def apple_callback(request):
    code  = request.POST.get("code")
    error = request.POST.get("error")

    if error or not code:
        messages.error(request, "No se pudo iniciar sesión con Apple.")
        return redirect('accounts:login')

    # Decode id_token to get user info (Apple sends JWT)
    id_token = request.POST.get("id_token", "")
    user_json = request.POST.get("user", "{}")

    try:
        # Decode JWT payload (middle part, base64)
        payload_b64 = id_token.split(".")[1]
        # Add padding
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        import base64
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        sub   = payload.get("sub")
        email = payload.get("email", "")
    except Exception:
        messages.error(request, "Error al procesar token de Apple.")
        return redirect('accounts:login')

    # Apple only sends name on first login
    try:
        user_data = json.loads(user_json)
        first = user_data.get("name", {}).get("firstName", "")
        last  = user_data.get("name", {}).get("lastName", "")
        full_name = f"{first} {last}".strip()
    except Exception:
        full_name = ""

    user = _get_or_create_social_user(
        provider    = "apple",
        provider_id = sub,
        email       = email,
        full_name   = full_name,
        avatar_url  = "",
    )

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, f"¡Bienvenido, {user.first_name or user.username}! Sesión iniciada con Apple.")
    return redirect('students:dashboard')