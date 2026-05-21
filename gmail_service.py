"""
gmail_service.py
----------------
Coloca este archivo en la raíz del proyecto (junto a manage.py),
o en cualquier app y ajusta el import en students/views.py.

Dependencias (agregar a requirements.txt):
    google-auth>=2.29.0
    google-auth-oauthlib>=1.2.0
    google-api-python-client>=2.126.0
"""

from __future__ import annotations

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.utils import timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


# ── Scopes requeridos ────────────────────────────────────────────────────────
# Agrega estos en settings.py → GOOGLE_OAUTH_SCOPES
# y en la pantalla de consentimiento de Google Cloud Console.
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def _get_credentials(social_account) -> Credentials | None:
    """
    Construye un objeto Credentials de Google a partir del SocialAccount.
    Refresca el access_token automáticamente si está vencido.
    Retorna None si no hay refresh_token guardado.
    """
    if not social_account.refresh_token:
        logger.warning(
            "SocialAccount %s no tiene refresh_token. "
            "El usuario debe volver a autenticarse con scope de Gmail.",
            social_account.pk,
        )
        return None

    creds = Credentials(
        token         = social_account.access_token or None,
        refresh_token = social_account.refresh_token,
        token_uri     = "https://oauth2.googleapis.com/token",
        client_id     = settings.GOOGLE_CLIENT_ID,
        client_secret = settings.GOOGLE_CLIENT_SECRET,
        scopes        = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            GMAIL_SEND_SCOPE,
        ],
    )

    # Refrescar si venció
    if not creds.valid:
        try:
            creds.refresh(Request())
            # Guardar el nuevo access_token en BD
            social_account.access_token  = creds.token
            social_account.token_expiry  = timezone.now() + timezone.timedelta(seconds=3600)
            social_account.save(update_fields=["access_token", "token_expiry"])
            logger.info("Token refrescado para SocialAccount %s", social_account.pk)
        except Exception as exc:
            logger.error("No se pudo refrescar el token: %s", exc)
            return None

    return creds


def _build_message(
    sender: str,
    to: str,
    subject: str,
    html_body: str,
    text_body: str = "",
) -> dict:
    """Construye el mensaje MIME listo para la API de Gmail."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def send_gmail_message(
    teacher_user,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
) -> bool:
    """
    Envía un correo usando la cuenta Gmail del docente autenticado con Google OAuth.

    Args:
        teacher_user: instancia de django.contrib.auth.models.User
        to_email:     destinatario
        subject:      asunto
        html_body:    cuerpo HTML
        text_body:    cuerpo texto plano (opcional, fallback)

    Returns:
        True si el envío fue exitoso, False en cualquier error.
    """
    # 1. Obtener el SocialAccount de Google del docente
    try:
        social = teacher_user.social_accounts.get(provider="google")
    except teacher_user.social_accounts.model.DoesNotExist:
        logger.warning(
            "El usuario %s no tiene cuenta Google vinculada.", teacher_user.pk
        )
        return False

    # 2. Construir credenciales
    creds = _get_credentials(social)
    if creds is None:
        return False

    # 3. Construir el servicio Gmail
    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as exc:
        logger.error("Error construyendo servicio Gmail: %s", exc)
        return False

    # 4. Enviar
    sender_email = social.email or teacher_user.email
    message = _build_message(sender_email, to_email, subject, html_body, text_body)

    try:
        service.users().messages().send(userId="me", body=message).execute()
        logger.info(
            "Gmail enviado de %s a %s — asunto: %s",
            sender_email, to_email, subject,
        )
        return True
    except HttpError as exc:
        logger.error("HttpError enviando Gmail: %s", exc)
        return False
    except Exception as exc:
        logger.error("Error inesperado enviando Gmail: %s", exc)
        return False