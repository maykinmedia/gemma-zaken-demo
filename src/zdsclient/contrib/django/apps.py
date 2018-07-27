from django.apps import AppConfig
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured

from zdsclient.conf import settings


class ZDSClientConfig(AppConfig):
    name = 'zdsclient.contrib.django'

    def ready(self):
        initialize_settings()


def initialize_settings():
    config = getattr(django_settings, 'ZDSCLIENT_CONFIG', None)
    if config is None:
        raise ImproperlyConfigured('The Django settings file should have a ZDSCLIENT_CONFIG variable. If you rely on '
                                   'a "config.yml" file, just remove "zdsclient.contrib.django" from '
                                   'INSTALLED_SETTINGS.')

    settings.config.update(config)
