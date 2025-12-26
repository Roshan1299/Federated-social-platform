"""
Django settings for the Federated Social Platform project.

This file contains all the configuration settings for the Django project.
It includes settings for databases, authentication, static files, and more.
For more information on this file, see:
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see:
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-$1!7u=+j37z@amy)z%)bjl!!v=uti_1d46!+39=0a+s_*0)t!j'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Set this in  Heroku Config Vars (replace with your app url and name)
#   heroku config:set BASE_URL=https://darkblue-s.herokuapp.com -a darkblue
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'authors.apps.AuthorsConfig',
    'django.contrib.humanize'
]

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

ROOT_URLCONF = 'social_distribution.urls'

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
                'authors.context_processors.pending_follow_requests_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'social_distribution.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

if os.environ.get("DATABASE_URL") != None:
    # Running on Heroku
    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True
        )
    }
else:
    # Running locally.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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

# Remote Nodes Configuration
# Configuration for connecting to other federated nodes
REMOTE_NODES = [
    {
        "host": "https://node-b.herokuapp.com",   # Remote host (or localhost:8001)
        "auth": "bm9kZWJfdXNlcjpzdXBlcl9zZWNyZXRfcHc="  # base64("nodeb_user:super_secret_pw")
    }
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# User Uploaded Media files
# Source: Codemy.com Django Profile Pictures Tutorial : https://www.youtube.com/watch?v=CA5duCGDSUE
MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'authors.Author'

# Logout redirect
LOGOUT_REDIRECT_URL = 'login'

# Federation base URL used to build canonical URLs for authors/posts/likes/etc.
# In production (Heroku), set BASE_URL in your config vars to:
#   https://dark-blue1-74095fb398f8.herokuapp.com
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")