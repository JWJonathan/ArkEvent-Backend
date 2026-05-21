import os
from pathlib import Path
import environ

# Initialize environ
env = environ.Env(
    DEBUG=(bool, False)
)

# === Environnement ===
ENV = os.getenv("DJANGO_ENV", "development")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
DOCKER = os.getenv("DOCKER", "False") == "True"

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
SECRET_KEY = env('SECRET_KEY', default='django-insecure-fallback-key-change-me')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'corsheaders',

    # Local apps
    'apps.core',
    'apps.users',
    'apps.organization',
    'apps.events',
    'apps.tickets',
    'apps.payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'arkevent_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'arkevent_backend.wsgi.application'
ASGI_APPLICATION = 'arkevent_backend.asgi.application'

from supabase import create_client, Client

# ====== Supabase Client Configuration ======
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'http://supabase-kong:8000')
SUPABASE_PUBLIC_URL = os.environ.get('SUPABASE_PUBLIC_URL', 'http://localhost:8001')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
SUPABASE_JWT_SECRET = os.environ.get('SUPABASE_JWT_SECRET')

# Supabase Storage compatible S3
SUPABASE_S3_ENDPOINT_URL = 'https://supabase.arkht.com/storage/v1/s3'
SUPABASE_S3_ACCESS_KEY_ID = os.environ.get('S3_PROTOCOL_ACCESS_KEY_ID')
SUPABASE_S3_SECRET_ACCESS_KEY = os.environ.get('S3_PROTOCOL_ACCESS_KEY_SECRET')
SUPABASE_BUCKET_NAME = 'nom-de-votre-bucket'
SUPABASE_S3_REGION = 'us-east-1'  # ou autre, Supabase l'ignore
# Optionnel : domaine personnalisé pour les URLs publiques (si configuré)
SUPABASE_S3_CUSTOM_DOMAIN = None   # ou 'cdn.supabase.arkht.com' si tu as un CDN

# Pour éviter les conflits de noms (chaque upload aura un chemin unique)
SUPABASE_FILE_OVERWRITE = False

if not DEBUG:
    # Initialisation du client Supabase (Backend - Admin)
    supabase_admin: Client = create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_KEY
    )

    # Client public (pour les opérations non-admin si nécessaire)
    supabase_public: Client = create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY
    )

if DOCKER:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('SUPABASE_DB_NAME', 'agrisen_db'),
            'USER': os.getenv('SUPABASE_DB_USER', 'agrisen_user'),
            'PASSWORD': os.getenv('SUPABASE_DB_PASSWORD', ''),
            'HOST': os.getenv('SUPABASE_DB_HOST', 'supabase-pooler'),
            'PORT': os.getenv('SUPABASE_DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'options': '-c search_path=agrisen,public'
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', 'arkevent'),
            'USER': os.getenv('DATABASE_USER', 'arkevent_dev'),
            'PASSWORD': os.getenv('DATABASE_PASSWORD', '1234jonathan'),
            'HOST': os.getenv('DATABASE_HOST', 'localhost'),
            'PORT': os.getenv('DATABASE_PORT', '5432'),
            'CONN_MAX_AGE': 600,
        }
    }

print("DOCKER =", DOCKER)
print("DB HOST =", os.environ.get("SUPABASE_DB_HOST"))

# Supabase Settings
SUPABASE_URL = env('SUPABASE_URL', default='')
SUPABASE_JWT_SECRET = env('SUPABASE_JWT_SECRET', default='')
SUPABASE_SERVICE_ROLE_KEY = env('SUPABASE_SERVICE_ROLE_KEY', default='')

# PayPal Settings
PAYPAL_CLIENT_ID = env('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = env('PAYPAL_CLIENT_SECRET', default='')
PAYPAL_WEBHOOK_ID = env('PAYPAL_WEBHOOK_ID', default='')

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.core.auth.SupabaseJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': (
        'apps.core.renderers.CoreJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}

# Celery
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'release-expired-reservations-every-5-minutes': {
        'task': 'apps.tickets.tasks.release_expired_reservations',
        'schedule': crontab(minute='*/5'),
    },
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True  # For development

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
