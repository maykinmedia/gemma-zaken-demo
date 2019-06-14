import base64
import json
from collections import namedtuple
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from solo.models import SingletonModel
from vng_api_common.models import JWTSecret
from vng_api_common.notifications.models import (
    NotificationsConfig, Subscription
)
from zds_client import Client

ServiceConfig = namedtuple('ServiceConfig', ['base_url', 'client_id', 'secret'])


class NotifyMethod(DjangoChoices):
    # amqp_server = ChoiceItem('amqp_server', _('AMQP-server'))
    webhook = ChoiceItem('webhook', _('REST API callback (webhook)'))


class SiteConfiguration(SingletonModel):
    SERVICES = ['zrc', 'drc', 'ztc', 'brc', 'nc', 'vrl', 'orc', ]
    CLIENTS = {}

    global_api_client_id = models.CharField(
        _('Client ID'), max_length=255, blank=True,
        help_text=_('Deze Client ID wordt voor alle APIs gebruikt, tenzij een '
                    'API specifieke Client ID is opgegeven'))
    global_api_secret = models.CharField(
        _('Secret'), max_length=512, blank=True,
        help_text=_('Dit Secret wordt voor alle APIs gebruikt, tenzij een '
                    'API specifiek Secret is opgegeven'))
    google_maps_api_key = models.CharField(
        _('Google maps API-key'), max_length=255, blank=True)
    google_maps_lat = models.DecimalField(
        _('Google maps latitude'), max_digits=9, decimal_places=6, blank=True,
        default='52.369918')
    google_maps_long = models.DecimalField(
        _('Google maps longitude'), max_digits=9, decimal_places=6, blank=True,
        default='4.897787',
        help_text=_('Deze coördinaten worden standaard op de kaart weergegeven'))

    # ZRC-configuratie
    zrc_base_url = models.CharField(
        _('ZRC basis URL'), blank=True, default='http://localhost:8000/api/v1/',
        max_length=255,
        help_text=_('Zaken API van het Zaak registratie component'))
    zrc_client_id = models.CharField(
        _('Client ID'), max_length=255, blank=True)
    zrc_secret = models.CharField(
        _('Secret'), max_length=512, blank=True)

    # DRC-configuratie
    drc_base_url = models.CharField(
        _('DRC basis URL'), blank=True, default='http://localhost:8001/api/v1/',
        max_length=255,
        help_text=_('Documenten API van het Document registratie component'))
    drc_client_id = models.CharField(
        _('Client ID'), max_length=255, blank=True)
    drc_secret = models.CharField(
        _('Secret'), max_length=512, blank=True)

    # ZTC-configuratie
    ztc_base_url = models.CharField(
        _('ZTC basis URL'), blank=True, default='http://localhost:8002/api/v1/',
        max_length=255,
        help_text=_('Catalogus API van het Zaaktypecatalogus component'))
    ztc_client_id = models.CharField(
        _('Client ID'), max_length=255, blank=True)
    ztc_secret = models.CharField(
        _('Secret'), max_length=512, blank=True)
    ztc_catalogus_uuid = models.CharField(
        _('Standaard catalogus UUID'), max_length=36, blank=True,
        help_text=_('Het UUID van de catalogus in het ZTC'))

    # BRC-configuratie
    brc_base_url = models.CharField(
        _('BRC basis URL'), blank=True, default='http://localhost:8003/api/v1/',
        max_length=255,
        help_text=_('Besluit API van het Besluit registratie component'))
    brc_client_id = models.CharField(
        _('Client ID'), max_length=255, blank=True)
    brc_secret = models.CharField(
        _('Secret'), max_length=512, blank=True)

    # NC-configuratie
    callback_client_id = models.CharField(
        _('Callback Client ID'), max_length=255, blank=True,
        help_text=_('De Client ID van de webhook API van deze demo applicatie')
    )
    callback_secret = models.CharField(
        _('Callback Secret'), max_length=512, blank=True,
        help_text=_('De Secret van de webhook API van deze demo applicatie')
    )
    callback_url = models.URLField(
        _('Callback URL'), blank=True,
        help_text=_('De URL van deze demo applicatie waar het NRC berichten naar toe kan sturen.')
    )

    nc_method = models.CharField(
        _('Notificatie methode'), max_length=20, default=NotifyMethod.webhook)
    nc_base_url = models.CharField(
        _('NRC basis URL'), blank=True, default='http://localhost:8004/api/v1/', max_length=255,
        help_text=_('Notificatie API van het Notificatie routering component'))

    nc_client_id = models.CharField(
        _('Client ID'), max_length=255, blank=True)
    nc_secret = models.CharField(
        _('Secret'), max_length=512, blank=True)

    nc_amqp_host = models.CharField(
        _('AMQP-host'), blank=True, max_length=255,
        help_text=_('Verbind direct met AMQP-server via deze host.'))
    nc_amqp_port = models.CharField(
        _('AMQP-port'), blank=True, default='', max_length=255,
        help_text=_('Verbind direct met AMQP-server via deze port.'))

    # VRL-configuratie
    vrl_base_url = models.CharField(
        _('VRL basis URL'), blank=True, default='https://ref.tst.vng.cloud/referentielijsten/api/v1/',
        max_length=255,
        help_text=_('VNG Referentielijsten API: Typisch de landelijke API URL en niet een eigen installatie.'))

    # ORC-configuratie
    orc_base_url = models.CharField(
        _('ORC basis URL'), blank=True, default='http://localhost:8010/api/v1/',
        max_length=255,
        help_text=_('Zaken API van het Zaak registratie component'))
    orc_client_id = models.CharField(
        _('Client ID'), max_length=255, blank=True)
    orc_secret = models.CharField(
        _('Secret'), max_length=512, blank=True)

    # MOR-configuratie
    zrc_bronorganisatie = models.CharField(max_length=9, default='517439943')

    ztc_mor_zaaktype_uuid = models.CharField(
        _('Zaaktype "Melding Openbare Ruimte" UUID'), max_length=36, blank=True)
    ztc_mor_statustype_new_uuid = models.CharField(
        _('Statustype "Nieuw" UUID'), max_length=36, blank=True)
    ztc_mor_informatieobjecttype_image_uuid = models.CharField(
        _('Informatieobjecttype "Afbeelding" UUID'), max_length=36, blank=True)

    class Meta:
        verbose_name = _('Configuratie')

    def clean(self):
        if self.nc_method == NotifyMethod.webhook:
            if not self.nc_base_url:
                raise ValidationError(_('Bij "webhook" als notificatie methode moet de "NRC basis URL" ingevuld zijn.'))
        else:
            if not self.nc_amqp_host:
                raise ValidationError(_('Bij "AMQP-server" als notificatie methode moet de "AMQP-host" ingevuld zijn.'))

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # To use the mechanics in vng-api-common, we create a JWTSecret object
        # so we don't need to implement our own authentication layer for the
        # notification callback API.
        if self.callback_client_id and self.callback_secret:
            JWTSecret.objects.update_or_create(
                identifier=self.callback_client_id,
                defaults={
                    'secret': self.callback_secret,
                }
            )

        # Create NotificationConfig to store the NC.
        notifications_config = NotificationsConfig.get_solo()
        if self.nc_base_url:
            notifications_config.api_root = self.nc_base_url
            notifications_config.client_id = self.nc_client_id or self.global_api_client_id
            notifications_config.secret = self.nc_secret or self.global_api_secret
            notifications_config.save()

        # Create Subscription based on details here with default channel and
        # topics.
        try:
            Subscription.objects.update_or_create(
                config=notifications_config,
                defaults={
                    'callback_url': self.callback_url,
                    'client_id': self.callback_client_id,
                    'secret': self.callback_secret,
                    'channels': ['zaken', ]
                }
            )
        except Subscription.MultipleObjectsReturned:
            # Manual configuration needed
            pass

    def reload_config(self):
        self.__class__.CLIENTS.clear()

        config = self.get_zdsclient_config()
        Client.load_config(**config)

    def get_nc_channels_and_filters(self):
        # return [(ex.name, ex.get_filters()) for ex in self.exchange_set.all()]
        return ['zaken', [{'foo.bar'}, {'bar.foo'}, ]]

    def get_service_config(self, service):
        """
        Returns a `ServiceConfig` for given `service`.

        :param service: The service name.
        :return: A `ServiceConfig`.
        """
        base_url = getattr(self, '{}_base_url'.format(service))
        client_id = getattr(self, '{}_client_id'.format(service), None)
        if not client_id:
            client_id = self.global_api_client_id
        secret = getattr(self, '{}_secret'.format(service), None)
        if not secret:
            secret = self.global_api_secret

        return ServiceConfig(base_url, client_id, secret)

    def get_zdsclient_config(self):
        """
        Returns the ZDSClient configuration format.
        """
        result = {}
        for service in self.SERVICES:
            service_config = self.get_service_config(service)
            if service_config.base_url:
                o = urlparse(service_config.base_url)
                result[service] = {
                    'host': o.hostname,
                    'scheme': o.scheme,
                }
                # TODO: Workaround for required port
                if o.port:
                    result[service]['port'] = o.port
                elif o.scheme == 'https':
                    result[service]['port'] = 443
                else:
                    result[service]['port'] = 80

                if service_config.client_id and service_config.secret:
                    result[service]['auth'] = {
                        'client_id': service_config.client_id,
                        'secret': service_config.secret,
                        'user_id': 'anonymous',
                        'user_representation': 'Anonymous'
                    }

        return result

    def get_services(self):
        """
        Returns a dict with all services (configured or not).
        """
        result = {}
        for service in self.SERVICES:
            base_url = getattr(self, f'{service}_base_url')
            result[service] = base_url

        return result

    def get_client(self, service):
        """
        Return a properly configured `Client` instance.

        :param service: The service key for this client.
        :return: A `Client` instance.
        """
        base_url = getattr(self, '{}_base_url'.format(service))
        base_path = ''
        if base_url:
            o = urlparse(base_url)
            base_path = o.path

        return Client(service, base_path)


class OtherZTC(models.Model):
    config = models.ForeignKey('demo.SiteConfiguration', on_delete=models.CASCADE)

    base_url = models.CharField(
        _('ZTC basis URL'), blank=True, max_length=255,
        help_text=_('Catalogus API van het Zaaktypecatalogus component'))
    client_id = models.CharField(
        _('Client ID'), max_length=255, blank=True)
    secret = models.CharField(
        _('Secret'), max_length=512, blank=True)

    class Meta:
        verbose_name = 'Overige ZTC'
        verbose_name_plural = 'Overige ZTC\'s'

    def get_client(self):
        """
        Return a properly configured `Client` instance.

        :return: A `Client` instance.
        """
        base_path = ''
        if self.base_url:
            o = urlparse(self.base_url)
            base_path = o.path

        return Client('ztc', base_path)


def validate_filters(value):
    if not value:
        return

    try:
        data = json.loads(value)
    except ValueError:
        raise ValidationError(
            _('Ongeldig JSON formaat'),
        )

    if not isinstance(data, list):
        raise ValidationError(
            _('Filters moeten worden opgegeven als "objecten" in een "lijst".'),
        )

    for element in data:
        if not isinstance(element, dict):
            raise ValidationError(
                _('Filters moeten worden opgegeven als "objecten" in een "lijst".'),
            )


def client(service, url=None, request=None):
    """
    Helper function to grab the properly configured `Client` instance.

    :param service: The service key for this client.
    :param url: The url to request, to get a matching client.
    :return: A `Client` instance.
    """

    if service not in SiteConfiguration.CLIENTS:
        config = SiteConfiguration.get_solo()
        SiteConfiguration.CLIENTS[service] = {
            'DEFAULT': config.get_client(service)
        }

        attr = f'other{service}_set'
        if hasattr(config, attr):
            other_config_set = getattr(config, attr).all()
            for other_config in other_config_set:
                SiteConfiguration.CLIENTS[service][other_config.base_url] = \
                    other_config.get_client()

    client_res = None
    if url:
        for base_url, client in SiteConfiguration.CLIENTS[service].items():
            if url.startswith(base_url):
                client_res = client
                break

    client_res = client_res or SiteConfiguration.CLIENTS[service]['DEFAULT']
    if not request:
        return client_res

    # add user_id and user_representation from request
    if request.user.is_authenticated:
        client_res.auth.user_id = request.user.username
        client_res.auth.user_representation = request.user.get_full_name()
    else:
        client_res.auth.user_id = 'anonymous'
        client_res.auth.user_representation = 'anonymous'
    return client_res
