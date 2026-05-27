import os
from pathlib import Path

from dotenv import load_dotenv
import dj_database_url

import cloudinary
import cloudinary.uploader
import cloudinary.api

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# .env
# ============================================================

load_dotenv(BASE_DIR / '.env')

# ============================================================
# CORE
# ============================================================

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-mentore-change-this-in-production-2024'
)

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    '.onrender.com',
    '127.0.0.1',
    'localhost',
]

# ============================================================
# APPS
# ============================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    'cloudinary_storage',

    'django.contrib.staticfiles',

    'cloudinary',

    'accounts',
    'students',
    'grades',
    'ai_assistant',
    'gallery',
    'calendar_app',
    'coordinator',
]

# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================================
# URLS / WSGI
# ============================================================

ROOT_URLCONF = 'mentore.urls'

WSGI_APPLICATION = 'mentore.wsgi.application'

# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ============================================================
# DATABASE
# ============================================================

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Render / producción
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Local
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ============================================================
# PASSWORDS
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'
    },
]

# ============================================================
# LANGUAGE
# ============================================================

LANGUAGE_CODE = 'es-co'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True

# ============================================================
# STATIC
# ============================================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static'
]

STATIC_ROOT = BASE_DIR / 'staticfiles'


# ============================================================
# CLOUDINARY
# ============================================================

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}

cloudinary.config(
    cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=CLOUDINARY_STORAGE['API_KEY'],
    api_secret=CLOUDINARY_STORAGE['API_SECRET'],
    secure=True,
)

# ============================================================
# MEDIA / CLOUDINARY
# ============================================================

import cloudinary
import cloudinary.uploader
import cloudinary.api

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}

cloudinary.config(
    cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=CLOUDINARY_STORAGE['API_KEY'],
    api_secret=CLOUDINARY_STORAGE['API_SECRET'],
    secure=True,
)

# LOCAL
if DEBUG:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# RENDER / PRODUCCIÓN
else:
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# CACHE
# ============================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'mentore-default',
    }
}

AI_CHAT_MAX_REQUESTS_PER_MINUTE = 8
AI_CHAT_RATE_WINDOW_SEC = 60
AI_CHAT_IN_FLIGHT_TTL = 180

# ============================================================
# AUTH
# ============================================================

LOGIN_URL = '/accounts/login/'

LOGIN_REDIRECT_URL = '/dashboard/'

LOGOUT_REDIRECT_URL = '/accounts/login/'

# ============================================================
# APIs
# ============================================================

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')

# ============================================================
# GOOGLE OAUTH
# ============================================================

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')

GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

# ============================================================
# APPLE LOGIN
# ============================================================

APPLE_CLIENT_ID = os.environ.get('APPLE_CLIENT_ID', '')

APPLE_CLIENT_SECRET = os.environ.get('APPLE_CLIENT_SECRET', '')

# ============================================================
# SECURITY
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
]

SECURE_PROXY_SSL_HEADER = (
    'HTTP_X_FORWARDED_PROTO',
    'https'
)

# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },

        'simple': {
            'format': '{levelname} {name}: {message}',
            'style': '{',
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },

        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'mentore.log',
            'formatter': 'verbose',
        },
    },

    'loggers': {
        'ai_assistant': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },

        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}