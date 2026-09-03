"""Django settings for SpotAxis.

All environment-specific values come from environment variables (a local
``.env`` file is loaded for development). See ``.env.example`` for the full
list. Nothing in this file should ever need to change between environments.
"""
import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_PATH = str(BASE_DIR / 'TRM')  # legacy alias used by a few modules

load_dotenv(BASE_DIR / '.env')


def env(name, default=None):
    value = os.getenv(name)
    return default if value is None or value == '' else value


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None or value == '':
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [item.strip() for item in (os.getenv(name) or default).split(',') if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
PROJECT_NAME = 'SpotAxis'
ENVIRONMENT = env('ENVIRONMENT', 'local_development')
DEBUG = env_bool('DEBUG', ENVIRONMENT in ('local_development', 'server_development'))

SECRET_KEY = env('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'insecure-development-key-do-not-use-in-production'
    else:
        raise ImproperlyConfigured('SECRET_KEY environment variable must be set when DEBUG is off.')

ON_RAILWAY = bool(os.getenv('RAILWAY_ENVIRONMENT'))

ADMINS = [tuple(item.split(':', 1)) for item in env_list('ADMINS') if ':' in item]
MANAGERS = ADMINS

TIME_ZONE = env('TIME_ZONE', 'UTC')
LANGUAGE_CODE = env('LANGUAGE_CODE', 'en')
LANGUAGES = (('en', 'English'),)
SITE_ID = 1
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Hosts and URLs
# ---------------------------------------------------------------------------
# SITE_SUFFIX is the suffix appended to a company slug to build its careers
# site host, e.g. ".spotaxis.com/" -> "acme.spotaxis.com". The host part of
# SITE_SUFFIX (without the leading dot and trailing slash) is the main site.
SITE_SUFFIX = env('SITE_SUFFIX', env('site_suffix', '.spotaxis.localhost:8010/' if DEBUG else '.spotaxis.com/'))
MAIN_HOST = SITE_SUFFIX.strip('/').lstrip('.')
ROOT_DOMAIN = env('ROOT_DOMAIN', MAIN_HOST.split(':')[0].split('.')[0])
PROTOCOL = env('PROTOCOL', 'http' if DEBUG else 'https')
SITE_URL = env('SITE_URL', env('site_url', f'{PROTOCOL}://{MAIN_HOST}'))
HOSTED_URL = env('HOSTED_URL', SITE_URL)

# Extra hosts (besides MAIN_HOST) that should serve the main site, e.g. the
# platform-provided domain on Railway before a custom domain is attached.
MAIN_HOSTS = {MAIN_HOST.split(':')[0]} | set(env_list('MAIN_HOSTS'))
if os.getenv('RAILWAY_PUBLIC_DOMAIN'):
    MAIN_HOSTS.add(os.getenv('RAILWAY_PUBLIC_DOMAIN'))

_default_allowed = '.spotaxis.localhost,localhost,127.0.0.1' if DEBUG else ''
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', _default_allowed) + sorted(MAIN_HOSTS)
if MAIN_HOST.split(':')[0] not in ('localhost', '127.0.0.1'):
    # Allow every company subdomain of the main host.
    ALLOWED_HOSTS.append('.' + MAIN_HOST.split(':')[0])
if ON_RAILWAY:
    ALLOWED_HOSTS.append('healthcheck.railway.app')
ALLOWED_HOSTS = sorted(set(ALLOWED_HOSTS))

CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
if not CSRF_TRUSTED_ORIGINS:
    _bare_main = MAIN_HOST.split(':')[0]
    CSRF_TRUSTED_ORIGINS = [f'{PROTOCOL}://{host}' for host in sorted(MAIN_HOSTS)]
    CSRF_TRUSTED_ORIGINS.append(f'{PROTOCOL}://*.{_bare_main}')
    if DEBUG and ':' in MAIN_HOST:
        CSRF_TRUSTED_ORIGINS.append(f'{PROTOCOL}://{MAIN_HOST}')
        CSRF_TRUSTED_ORIGINS.append(f'{PROTOCOL}://*.{MAIN_HOST}')

ROOT_URLCONF = 'TRM.urls'
SUBDOMAIN_URLCONF = 'TRM.subdomain_urls'
WSGI_APPLICATION = 'TRM.wsgi.application'

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.humanize',
    'core',
    'companies',
    'candidates',
    'common',
    'vacancies',
    'activities',
    'upload_logos',
    'ckeditor',
    'payments',
    'scheduler',
    'customField',
    'django_extensions',
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'TRM.middleware.SubdomainMiddleware',
    'TRM.middleware.MediumMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(PROJECT_PATH, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'TRM.context_processors.project_name',
                'TRM.context_processors.user_profile',
                'TRM.context_processors.candidate_full_name',
                'TRM.context_processors.logo_candidate_default',
                'TRM.context_processors.logo_company_default',
                'TRM.context_processors.subdomain',
                'TRM.context_processors.notifications',
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database (DATABASE_URL, e.g. postgres://user:pass@host:5432/dbname)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': dj_database_url.config(
        default='postgres://localhost:5432/spotaxis',
        conn_max_age=int(env('DB_CONN_MAX_AGE', '600')),
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'common.User'
AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)
LOGIN_URL = '/login/'
LOGIN_ERROR_URL = '/login/'
LOGIN_REDIRECT_URL = 'common_redirect_after_login'
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_COOKIE_DOMAIN = env('SESSION_COOKIE_DOMAIN', env('session_cookie_domain'))
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # a few legacy templates read the cookie from JS
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Transport security (only when serving over HTTPS behind a proxy)
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = 'SAMEORIGIN'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SECURE_REDIRECT_EXEMPT = [r'^healthz/?$']
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env('SECURE_HSTS_SECONDS', '3600'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
    SECURE_HSTS_PRELOAD = False

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = env('STATIC_ROOT', str(BASE_DIR / 'staticfiles'))
STATICFILES_DIRS = [os.path.join(PROJECT_PATH, 'static')]
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 30
WHITENOISE_USE_FINDERS = DEBUG  # serve from app static dirs without collectstatic in development

MEDIA_ROOT = env('MEDIA_ROOT', env('media_root', str(BASE_DIR / 'media')))
MEDIA_URL = env('MEDIA_URL', env('media_url', '/media/'))
# Serve uploaded files through Django. Fine for development and for the
# ephemeral staging disk; object storage replaces this in Phase 1.
SERVE_MEDIA = env_bool('SERVE_MEDIA', True)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
MAX_UPLOAD_SIZE = 5 * 1024 * 1024

PHOTO_USER_DEFAULT = 'logos_TRM/logo_TRM_user_default.png'
LOGO_CANDIDATE_DEFAULT = 'logos_TRM/logo_TRM_user_default.png'
LOGO_COMPANY_DEFAULT = 'logos_TRM/logo_TRM_company_default.png'
DEFAULT_SITE_TEMPLATE = 1
CKEDITOR_UPLOAD_PATH = 'uploads/'

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    env('email_backend', 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'),
)
EMAIL_HOST = env('EMAIL_HOST', env('email_host', 'localhost'))
EMAIL_PORT = int(env('EMAIL_PORT', env('email_port', '587')))
EMAIL_HOST_USER = env('EMAIL_HOST_USER', env('email_host_user', ''))
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', env('email_host_passw', ''))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', env_bool('email_use_tls', True))
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', env('default_from_email', f'{PROJECT_NAME} <noreply@{MAIN_HOST.split(":")[0]}>'))
SERVER_EMAIL = env('SERVER_EMAIL', env('server_email', DEFAULT_FROM_EMAIL))
NOTIFICATION_EMAILS = env('NOTIFICATION_EMAILS', env('notification_emails'))
logo_email = env('LOGO_EMAIL', env('logo_email'))

# ---------------------------------------------------------------------------
# Legacy application settings still read by existing views
# ---------------------------------------------------------------------------
number_objects_page = 20
num_pages = 8
days_default_search = 30
PAYPAL_CLIENT_ID = env('PAYPAL_CLIENT_ID')
PAYPAL_APP_SECRET = env('PAYPAL_APP_SECRET')

# ---------------------------------------------------------------------------
# Scheduled tasks: POST /internal/tasks/run with this token to run due tasks
# ---------------------------------------------------------------------------
TASK_RUNNER_TOKEN = env('TASK_RUNNER_TOKEN')

# ---------------------------------------------------------------------------
# Logging and error reporting
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plain': {'format': '%(asctime)s %(levelname)s %(name)s %(message)s'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'},
    },
    'root': {'handlers': ['console'], 'level': env('LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}

SENTRY_DSN = env('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        traces_sample_rate=float(env('SENTRY_TRACES_SAMPLE_RATE', '0.05')),
        send_default_pii=False,
    )
