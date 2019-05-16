"""
Any machine specific settings when using development settings.
"""
from .settings import *
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
DJANGO_PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
BASE_DIR = os.path.abspath(os.path.join(DJANGO_PROJECT_DIR, os.path.pardir, os.path.pardir))

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'zac'),
        'USER': os.getenv('DB_USER', 'zac'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'zac'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', 5432),
    }
}

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'ec_w%f)(6t3_-y17oo!lkh-9x@5)_jdp)(n68hvj^$rrhrjj-o'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Add the hostnames or IP addresses that access this web application here.
ALLOWED_HOSTS = []

#
# Project specific settings
#
