from urllib.parse import urlparse

from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel


class SiteConfiguration(SingletonModel):
    SERVICES = ['zrc', 'drc', 'ztc', 'orc', 'brc']

    google_api_key = models.CharField(
        _('Google API-key'), max_length=255, blank=True)

    # APIs
    zrc_base_url = models.URLField(
        _('ZRC basis URL'), blank=True,default='http://localhost:8000',
        help_text=_('Zaken API van het Zaak registratie component'))
    drc_base_url = models.URLField(
        _('DRC basis URL'), blank=True, default='http://localhost:8001',
        help_text=_('Documenten API van het Document registratie component'))
    ztc_base_url = models.URLField(
        _('ZTC basis URL'), blank=True, default='http://localhost:8002',
        help_text=_('Catalogus API van het Zaaktypecatalogus component'))
    brc_base_url = models.URLField(
        _('BRC basis URL'), blank=True, default='http://localhost:8003',
        help_text=_('Besluit API van het Besluit registratie component'))
    orc_base_url = models.URLField(
        _('ORC basis URL'), blank=True, default='http://localhost:8888',
        help_text=_('Zaken API van het Zaak registratie component'))

    # ZRC-configuratie
    zrc_bronorganisatie = models.CharField(max_length=9, default='517439943')

    # ZTC-configuratie
    ztc_catalogus_uuid = models.CharField(
        _('Standaard catalogus UUID'), max_length=36, blank=True,
        help_text=_('Het UUID van de catalogus in het ZTC'))

    # MOR-configuratie
    ztc_mor_zaaktype_uuid = models.CharField(
        _('Zaaktype "Melding Openbare Ruimte" UUID'), max_length=36, blank=True)
    ztc_mor_statustype_new_uuid = models.CharField(
        _('Statustype "Nieuw" UUID'), max_length=36, blank=True)
    ztc_mor_informatieobjecttype_image_uuid = models.CharField(
        _('Informatieobjecttype "Afbeelding" UUID'), max_length=36, blank=True)

    class Meta:
        verbose_name = _('Configuratie')

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
                    'port': o.port,
                    'scheme': o.scheme,
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
