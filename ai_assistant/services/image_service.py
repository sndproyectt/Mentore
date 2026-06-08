"""
Servicio de generación de imágenes para Mentore IA.

Usa la API de Hugging Face (modelo FLUX.1-schnell)
para generar imágenes educativas a partir de prompts de texto.
"""
import base64
import logging
import requests

from django.conf import settings

logger = logging.getLogger(__name__)

# Modelo de generación de imágenes de Hugging Face
IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
# Usamos el nuevo router oficial de Hugging Face que tiene mejor resolución DNS global
HF_BASE_URL = "https://router.huggingface.co/hf-inference/models"

def is_configured():
    """Verifica si la API de Hugging Face está configurada para generación de imágenes."""
    api_key = getattr(settings, 'HUGGINGFACE_API_KEY', '')
    return bool(api_key and api_key.strip())

def generate_image(prompt, user=None):
    """
    Genera una imagen usando Hugging Face Inference API.

    Args:
        prompt: Descripción de la imagen a generar
        user: Usuario Django (para logging)

    Returns:
        dict: {
            'success': bool,
            'image_data': str (base64),  # si success
            'mime_type': str,             # si success
            'text': str,                  # texto acompañante si lo hay
            'error': str,                 # si !success
            'retry_after': int            # opcional si falla por rate limit
        }
    """
    api_key = getattr(settings, 'HUGGINGFACE_API_KEY', '')
    if not api_key:
        return {
            'success': False,
            'error': (
                '⚠️ La generación de imágenes no está configurada. '
                'Agrega HUGGINGFACE_API_KEY en el archivo .env'
            ),
        }

    url = f"{HF_BASE_URL}/{IMAGE_MODEL}"

    # Enriquecer el prompt para contexto educativo
    enhanced_prompt = (
        f"{prompt}, "
        "high quality, colorful, suitable for primary school education, safe for children."
    )

    payload = {
        "inputs": enhanced_prompt,
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    username = user.username if user else "anónimo"
    logger.info(
        "Generación de imagen solicitada a Hugging Face por %s: '%s...'",
        username, prompt[:80],
    )

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)

        if resp.status_code == 429:
            logger.warning("Hugging Face imagen: rate limit alcanzado")
            
            error_data = {}
            try:
                error_data = resp.json()
            except Exception:
                pass
            
            error_msg = error_data.get('error', 'Límite de la API excedido')
            
            retry_after = resp.headers.get('Retry-After', 60)
            try:
                retry_after = int(retry_after)
            except ValueError:
                retry_after = 60
                
            return {
                'success': False,
                'error': (
                    '⏳ Se ha alcanzado el límite de solicitudes de Hugging Face. '
                    f'Espera <strong id="imgGenCountdown">{retry_after}</strong> segundos e intenta de nuevo. '
                ),
                'retry_after': retry_after,
            }
            
        if resp.status_code == 503:
            logger.info("Hugging Face imagen: modelo cargando")
            error_data = {}
            try:
                error_data = resp.json()
            except Exception:
                pass
            
            estimated_time = error_data.get('estimated_time', 20)
            return {
                'success': False,
                'error': (
                    f'⏳ El modelo de generación se está encendiendo en Hugging Face. '
                    f'Espera <strong id="imgGenCountdown">{int(estimated_time)}</strong> segundos e intenta de nuevo.'
                ),
                'retry_after': int(estimated_time)
            }

        if resp.status_code != 200:
            logger.error(
                "Hugging Face imagen HTTP %d: %s",
                resp.status_code, resp.text[:300],
            )
            
            error_data = {}
            try:
                error_data = resp.json()
            except Exception:
                pass
            error_msg = error_data.get('error', f'código {resp.status_code}')
            
            return {
                'success': False,
                'error': f'❌ Error en la generación: {error_msg}',
            }

        content_type = resp.headers.get("Content-Type", "")
        if "application/json" in content_type:
            data = resp.json()
            if isinstance(data, dict) and "error" in data:
                return {
                    'success': False,
                    'error': f"❌ Error de Hugging Face: {data['error']}"
                }
                
        image_bytes = resp.content
        if not image_bytes:
            return {
                'success': False,
                'error': '❌ Respuesta vacía del modelo.',
            }
            
        mime_type = content_type if "image" in content_type else "image/jpeg"
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        logger.info(
            "Imagen generada exitosamente (mime=%s, data_len=%d)",
            mime_type, len(image_bytes),
        )

        return {
            'success': True,
            'image_data': image_b64,
            'mime_type': mime_type,
            'text': '',
        }

    except requests.exceptions.Timeout:
        logger.error("Hugging Face imagen timeout")
        return {
            'success': False,
            'error': '⏳ La generación tardó demasiado. Intenta con una descripción más simple.',
        }
    except requests.exceptions.ConnectionError:
        logger.error("Hugging Face imagen: error de conexión")
        return {
            'success': False,
            'error': '🌐 Error de conexión a Hugging Face. Verifica tu internet e intenta de nuevo.',
        }
    except Exception as e:
        logger.exception("Hugging Face imagen error inesperado: %s", str(e))
        return {
            'success': False,
            'error': f'😔 Error inesperado: {str(e)}',
        }
