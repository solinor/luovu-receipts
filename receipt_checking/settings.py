"""
Django settings for receipt_checking project on Heroku. For more info, see:
https://github.com/heroku/heroku-django-template

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import json
import os
import sys

import dj_database_url

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

SECRET_KEY = os.environ.get("SECRET_KEY", "this-is-very-unsecure-default")

DEBUG = os.environ.get("DEBUG", False) in ("true", "True", True)

LUOVU_PARTNER_TOKEN = os.environ.get("LUOVU_PARTNER_TOKEN")
LUOVU_USERNAME = os.environ.get("LUOVU_USERNAME")
LUOVU_PASSWORD = os.environ.get("LUOVU_PASSWORD")
LUOVU_BUSINESS_ID = os.environ.get("LUOVU_BUSINESS_ID")

TAG_MANAGER_CODE = os.environ.get("TAG_MANAGER_CODE")

USER_EMAIL_MAP = json.loads(os.environ.get("USER_EMAIL_MAP", "{}"))

SLACK_BOT_ACCESS_TOKEN = os.environ.get("SLACK_BOT_ACCESS_TOKEN")
SLACK_ADMIN_EMAIL = os.environ.get("SLACK_ADMIN_EMAIL")

AUTHENTICATION_BACKENDS = (
    'googleauth.backends.GoogleAuthBackend',
)

# client ID from the Google Developer Console
GOOGLEAUTH_CLIENT_ID = os.environ.get("GOOGLEAUTH_CLIENT_ID")

# client secret from the Google Developer Console
GOOGLEAUTH_CLIENT_SECRET = os.environ.get("GOOGLEAUTH_CLIENT_SECRET")

# your app's domain, used to construct callback URLs
GOOGLEAUTH_CALLBACK_DOMAIN = os.environ.get("GOOGLEAUTH_CALLBACK_DOMAIN")

# callback URL uses HTTPS (your side, not Google), default True
GOOGLEAUTH_USE_HTTPS = os.environ.get("GOOGLEAUTH_USE_HTTPS", True) in (True, "True", "true")

# restrict to the given Google Apps domain, default None
GOOGLEAUTH_APPS_DOMAIN = os.environ.get("GOOGLEAUTH_APPS_DOMAIN")

# get user's name, default True (extra HTTP request)
GOOGLEAUTH_GET_PROFILE = True

# sets value of user.is_staff for new users, default False
GOOGLEAUTH_IS_STAFF = False

# list of default group names to assign to new users
GOOGLEAUTH_GROUPS = []

SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", 0))

INSTALLED_APPS = [
    "raven.contrib.django.raven_compat",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django_tables2',
    # Disable Django's own staticfiles handling in favour of WhiteNoise, for
    # greater consistency between gunicorn and `./manage.py runserver`. See:
    # http://whitenoise.evans.io/en/stable/django.html#using-whitenoise-in-development
    # 'whitenoise.runserver_nostatic',
    'googleauth',
    'django.contrib.staticfiles',
    'receipts',
    'compressor',
    'django_extensions',
]

REDIRECT_NEW_DOMAIN = os.environ.get("REDIRECT_NEW_DOMAIN")
REDIRECT_OLD_DOMAIN = os.environ.get("REDIRECT_OLD_DOMAIN")

CSP_DEFAULT_SRC = ("'none'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://www.gstatic.com", "https://www.google-analytics.com", "https://www.googletagmanager.com", "https://stats.g.doubleclick.net", "https://ajax.googleapis.com")
CSP_OBJECT_SRC = ("'self'",)  # required for PDF receipts
CSP_MEDIA_SRC = ("'none'",)
CSP_FRAME_SRC = ("'none'",)
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_CONNECT_SRC = ("'self'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://www.gstatic.com", "https://fonts.googleapis.com")
CSP_IMG_SRC = ("'self'", "https://stats.g.doubleclick.net", "https://www.google-analytics.com")
CSP_REPORT_URI = os.environ.get("CSP_REPORT_URI")
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

MIDDLEWARE = [
    'receipts.middleware.DomainRedirectMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'receipts.middleware.NoCacheHeaders'
]


ROOT_URLCONF = 'receipt_checking.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': DEBUG,
        },
    },
]

WSGI_APPLICATION = 'receipt_checking.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = False
USE_TZ = True

DATE_FORMAT = "Y-m-d"
SHORT_DATE_FORMAT = "Y-m-d"
DATETIME_FORMAT = "Y-m-d H:i"
SHORT_DATETIME_FORMAT = "Y-m-d H:i"

# Update database configuration with $DATABASE_URL.
DB_FROM_ENV = dj_database_url.config(conn_max_age=500)
DATABASES['default'].update(DB_FROM_ENV)

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", True) in (True, "True", "true")
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, 'static'),
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    "compressor.finders.CompressorFinder",
)

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'invoices': {
            'handlers': ['console'],
            'level': os.getenv('INVOICES_LOG_LEVEL', 'INFO'),
            'propagate': True,
        }
    },
}
