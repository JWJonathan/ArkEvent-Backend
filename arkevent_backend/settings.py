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
    'django.contrib.postgres',

    # Third party apps
    'rest_framework',
    'corsheaders',
    'storages',

    # Local apps
    'apps.core',
    'apps.users',
    'apps.organization',
    'apps.events',
    'apps.tickets',
    'apps.payments',
    'apps.notifications',
    'apps.marketing',
    'apps.registrations',
    'apps.networking',
    'apps.surveys',
    'apps.analytics',
    'apps.wallets',
    'apps.subscriptions',
    'apps.finance',
    'apps.marketplace',
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

AUTH_USER_MODEL = 'users.User'

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

BACKEND_URL = env('BACKEND_URL', default='http://127.0.0.1:8030')
API_URL = env('API_URL', default=BACKEND_URL + '/api/')

from supabase import create_client, Client

# ====== Supabase Client Configuration ======
SUPABASE_URL = env('SUPABASE_URL', default='http://supabase-kong:8000')
SUPABASE_PUBLIC_URL = env('SUPABASE_PUBLIC_URL', default='http://localhost:8001')
SUPABASE_ANON_KEY = env('SUPABASE_ANON_KEY', default='')
SUPABASE_SERVICE_KEY = env('SUPABASE_SERVICE_KEY', default='')
SUPABASE_JWT_SECRET = env('SUPABASE_JWT_SECRET', default='')

# Supabase Storage compatible S3
SUPABASE_S3_ENDPOINT_URL = env('SUPABASE_S3_ENDPOINT_URL', default='https://supabase.arkht.com/storage/v1/s3')
SUPABASE_S3_ACCESS_KEY_ID = env('S3_PROTOCOL_ACCESS_KEY_ID', default='')
SUPABASE_S3_SECRET_ACCESS_KEY = env('S3_PROTOCOL_ACCESS_KEY_SECRET', default='')
SUPABASE_BUCKET_NAME = env('SUPABASE_BUCKET_NAME', default='arkevent')
SUPABASE_S3_REGION = env('SUPABASE_S3_REGION', default='us-east-1')
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
                'options': '-c search_path=arkevent,public'
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DATABASE_NAME', 'arkevent'),
            'USER': os.getenv('DATABASE_USER', 'jwj'),
            'PASSWORD': os.getenv('DATABASE_PASSWORD', 'V@ultX9!r#7FpZ2m'),
            'HOST': os.getenv('DATABASE_HOST', 'localhost'),
            'PORT': os.getenv('DATABASE_PORT', '5432'),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'options': '-c search_path=arkevent,public'
            }
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

# Social Login Settings
GOOGLE_CLIENT_ID = env('GOOGLE_CLIENT_ID', default='')


INSTALLED_APPS += [
    'rest_framework_simplejwt',
] 

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # ← JWT standard
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
        'anon': '5000/day',
        'user': '100000/day'
    }
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,  # ← sécurité renforcée
    'BLACKLIST_AFTER_ROTATION': True,  # ← empêche la réutilisation
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(hours=1),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
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
    'schedule-event-reminders-every-hour': {
        'task': 'apps.notifications.tasks.schedule_event_reminders',
        'schedule': crontab(minute=0), # Every hour at minute 0
    },
    'schedule-post-event-notifications-daily': {
        'task': 'apps.notifications.tasks.schedule_post_event_notifications',
        'schedule': crontab(hour=10, minute=0), # Every day at 10 AM
    },
}

# Email Configuration
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@arkevent.com')
SERVER_EMAIL = env('SERVER_EMAIL', default='server@arkevent.com')

# Email Verification Settings
EMAIL_VERIFICATION_TIMEOUT_HOURS = env.int('EMAIL_VERIFICATION_TIMEOUT_HOURS', default=24)
EMAIL_VERIFICATION_CODE_LENGTH = 6

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

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Storage Configuration
if DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "access_key": SUPABASE_S3_ACCESS_KEY_ID,
                "secret_key": SUPABASE_S3_SECRET_ACCESS_KEY,
                "bucket_name": SUPABASE_BUCKET_NAME,
                "endpoint_url": SUPABASE_S3_ENDPOINT_URL,
                "region_name": SUPABASE_S3_REGION,
                "file_overwrite": SUPABASE_FILE_OVERWRITE,
                "custom_domain": SUPABASE_S3_CUSTOM_DOMAIN,
                "default_acl": None,
                "querystring_auth": False,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Dans vos settings.py ajoutez :
import sys

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}


CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=['https://backend.arkevent.arkht.com', 'http://backend.arkevent.arkht.com' ])
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['https://backend.arkevent.arkht.com', 'http://backend.arkevent.arkht.com' ])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Permettre à Django de savoir qu'on est en HTTPS derrière Nginx
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000