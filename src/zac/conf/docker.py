from django.core.exceptions import ImproperlyConfigured

from .settings import *

# Helper function
missing_environment_vars = []


def getenv(key, default=None, required=False, split=False):
    val = os.getenv(key, default)
    if required and val is None:
        missing_environment_vars.append(key)
    if split and val:
        val = val.split(',')
    return val


#
# Standard Django settings.
#
DEBUG = getenv('DEBUG', True)

ADMINS = getenv('ADMINS', split=True)
MANAGERS = ADMINS

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = getenv('ALLOWED_HOSTS', '*', split=True)

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'USER': getenv('DB_USER', 'postgres'),
        'NAME': getenv('DB_NAME', 'postgres'),
        'PASSWORD': getenv('DB_PASSWORD', ''),
        'HOST': getenv('DB_HOST', 'db'),
        'PORT': getenv('DB_PORT', '5432'),
    }
}

REDIS_HOST = getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(getenv('REDIS_PORT', 6379))
REDIS_DB_CACHE =  getenv('REDIS_DB_CACHE', 1)

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

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
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
    from .local import *
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
