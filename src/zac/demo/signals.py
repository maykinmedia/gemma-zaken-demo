import warnings

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models.signals import post_save
from django.dispatch import receiver
from vng_api_common.notifications.models import Subscription

from .models import SiteConfiguration


@receiver(post_save, sender=SiteConfiguration)
def update_settings(sender, instance, **kwargs):
    instance.reload_config()


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
            'SiteConfiguration could not be loaded. This happens when there '
            'are pending migrations. If this message occurs in any other '
            'situation, something went wrong: {}'.format(e))
        return

    update_settings(None, site_config)


@receiver(post_save, sender=Subscription)
def sync_config(sender, instance, **kwargs):
    """
    Keep the config in sync with what comes from VNG-API-Common.

    Use an update to prevent and endless back and forth sync. Does the job for
    now without making a real config UI effort.

    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    SiteConfiguration.objects.all().update(
        callback_url=instance.callback_url,
        callback_client_id=instance.client_id,
        callback_secret=instance.secret,
    )
