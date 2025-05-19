# settings.py (at the very top)
from django.utils.encoding import force_str
import django.utils.encoding
# alias force_text → force_str so fernet_fields can still import force_text
django.utils.encoding.force_text = force_str

from pathlib import Path
import environ, os

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)

# Load environment variables from .env if in debug
if env('DJANGO_DEBUG', default=False):
    environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY
SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG      = env.bool('DJANGO_DEBUG', default=False)

# OAuth credentials for third-party integrations
META_APP_ID         = env('META_APP_ID', default='')
META_APP_SECRET     = env('META_APP_SECRET', default='')  
GOOGLE_CLIENT_ID    = env('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET= env('GOOGLE_CLIENT_SECRET', default='')
SHOPIFY_API_KEY = env('SHOPIFY_API_KEY', default='')
SHOPIFY_API_SECRET = env('SHOPIFY_API_SECRET', default='')

ALLOWED_HOSTS = ['*']

# Django templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'django.contrib.sites','crispy_forms',
    'crispy_tailwind', 
    # third-party
    'allauth', 'allauth.account', 'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    "fernet_fields",
    # local
    'core',
    'django_celery_beat',
]

ROOT_URLCONF = "market_insights.urls"
SITE_ID = 1

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind", "bootstrap5"
CRISPY_TEMPLATE_PACK = "tailwind"

LOGIN_REDIRECT_URL = 'connect_data'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'

# Database / Redis / Celery
DATABASES = {'default': env.db()}
REDIS_URL = env('REDIS_URL')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Timezone
TIME_ZONE = "UTC"

# Static & media
STATIC_URL   = 'static/'
STATIC_ROOT  = BASE_DIR / 'staticfiles'
MEDIA_URL    = '/media/'
MEDIA_ROOT   = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery settings
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# WeasyPrint
WEASYPRINT_BASEURL = str(STATIC_ROOT)

# DeepSeek
DEEPSEEK_API_KEY = env("DEEPSEEK_API_KEY", default="YOUR_PLACEHOLDER_KEY")
