import warnings

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_save
from django.dispatch import receiver

from zds_client import Client

from .models import SiteConfiguration


@receiver(post_save, sender=SiteConfiguration)
def update_settings(sender, instance, **kwargs):
    config = instance.get_zdsclient_config()
    Client.load_config(django_settings.BASE_DIR, **config)


def initialize_settings():
    if 'zdsclient.contrib.django' in django_settings.INSTALLED_APPS:
        raise ImproperlyConfigured(
            'You cannot have both "zac.demo" and "zdsclient.contrib.django" in '
            'your INSTALLED_SETTINGS.')

    from zac.demo.models import SiteConfiguration

    try:
        site_config = SiteConfiguration.get_solo()
    except Exception as e:
        warnings.warn(
            'SiteConfiguration could not be loaded. This happens when the '
            'are pending migrations. If this message occurs in any other '
            'situation, something went wrong: {}'.format(e))
        return

    update_settings(None, site_config)
