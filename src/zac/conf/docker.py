import os

from django.core.exceptions import ImproperlyConfigured

os.environ.setdefault('DB_USER', 'postgres')
os.environ.setdefault('DB_NAME', 'postgres')
os.environ.setdefault('DB_PASSWORD', '')
os.environ.setdefault('DB_HOST', 'db')
os.environ.setdefault('DB_PORT', '5432')

os.environ.setdefault('ALLOWED_HOSTS', '*')

os.environ.setdefault('REDIS_HOST', 'redis')

from .settings import *  # noqa isort:skip

#
# Standard Django settings.
#


# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts

CACHES = {
    'default': {
        # 'LOCATION': getenv('CACHE_LOCATION', f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_CACHE}'),
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    # https://github.com/jazzband/django-axes/blob/master/docs/configuration.rst#cache-problems
    'axes_cache': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Deal with being hosted on a subpath
subpath = getenv('SUBPATH')
if subpath:
    if not subpath.startswith('/'):
        subpath = f'/{subpath}'

    FORCE_SCRIPT_NAME = subpath
    STATIC_URL = f"{FORCE_SCRIPT_NAME}{STATIC_URL}"
    # MEDIA_URL = f"{FORCE_SCRIPT_NAME}{MEDIA_URL}"

#
# Additional Django settings
#

# Disable security measures for development
SESSION_COOKIE_SECURE = getenv('SESSION_COOKIE_SECURE', False)
SESSION_COOKIE_HTTPONLY = getenv('SESSION_COOKIE_HTTPONLY', False)
CSRF_COOKIE_SECURE = getenv('CSRF_COOKIE_SECURE', False)

#
# Custom settings
#
ENVIRONMENT = 'docker'

# Override settings with local settings.
try:
    from .local import *  # noqa
except ImportError:
    pass


if missing_environment_vars:
    raise ImproperlyConfigured(
        'These environment variables are required but missing: {}'.format(', '.join(missing_environment_vars)))

#
# Library settings
#

# django-axes
AXES_BEHIND_REVERSE_PROXY = False
AXES_CACHE = 'axes_cache'

assert AXES_CACHE in CACHES
