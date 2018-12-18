from urllib.parse import urlparse

from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel
from zds_client import Client


class SiteConfiguration(SingletonModel):
    SERVICES = ['zrc', 'drc', 'ztc', 'orc', 'brc']
    CLIENTS = {}

    global_api_client_id = models.CharField(
        _('Client ID'), max_length=255, blank=True,
        help_text=_('Deze Client ID wordt voor alle APIs gebruikt, tenzij een '
                    'API specifieke Client ID is opgegeven'))
    global_api_secret = models.CharField(
        _('Secret'), max_length=512, blank=True,
        help_text=_('Dit Secret wordt voor alle APIs gebruikt, tenzij een '
                    'API specifiek Secret is opgegeven'))
    google_api_key = models.CharField(
        _('Google API-key'), max_length=255, blank=True)

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

    def reload_config(self):
        self.__class__.CLIENTS.clear()

        config = self.get_zdsclient_config()
        Client.load_config(**config)

    def get_zdsclient_config(self):
        """
        Returns the ZDSClient configuration format.
        """
        result = {}
        for service in self.SERVICES:
            base_url = getattr(self, '{}_base_url'.format(service))
            if base_url:
                o = urlparse(base_url)
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

                client_id = getattr(self, '{}_client_id'.format(service), None)
                if not client_id:
                    client_id = self.global_api_client_id
                secret = getattr(self, '{}_secret'.format(service), None)
                if not secret:
                    secret = self.global_api_secret

                if client_id and secret:
                    result[service]['auth'] = {
                        'client_id': client_id,
                        'secret': secret,
                        # Normally, you want to grab the scopes and claims from
                        # a role/scope mapping-service based on who is logged
                        # in. For demo purposes, we map anonymous (you don't
                        # have to login) to have all scopes and claims.
                        'scopes': [
                            'zds.scopes.zaken.lezen',
                            'zds.scopes.zaken.aanmaken',
                            'zds.scopes.statussen.toevoegen',
                            'zds.scopes.zaaktypes.lezen',
                        ],
                        'zaaktypes': [
                            '*',
                        ]
                    }

        return result

    def get_services(self):
        """
        Returns a dict with all services (configured or not).
        """
        result = {}
        for service in self.SERVICES:
            base_url = getattr(self, '{}_base_url'.format(service))
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


def client(service):
    """
    Helper function to grab the properly configured `Client` instance.

    :param service: The service key for this client.
    :return: A `Client` instance.
    """
    if service not in SiteConfiguration.CLIENTS:
        config = SiteConfiguration.get_solo()
        SiteConfiguration.CLIENTS[service] = config.get_client(service)

    return SiteConfiguration.CLIENTS[service]
