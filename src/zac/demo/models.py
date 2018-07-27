from urllib.parse import urlparse

from django.db import models
from django.utils.translation import ugettext_lazy as _

from solo.models import SingletonModel


class SiteConfiguration(SingletonModel):
    google_api_key = models.CharField(_('Google API-key'), max_length=255, blank=True)

    zrc_base_url = models.URLField(_('ZRC basis URL'), blank=True, default='http://localhost:8000')
    drc_base_url = models.URLField(_('DRC basis URL'), blank=True, default='http://localhost:8001')
    ztc_base_url = models.URLField(_('ZTC basis URL'), blank=True, default='http://localhost:8002')
    orc_base_url = models.URLField(_('ORC basis URL'), blank=True, default='http://localhost:8003')

    zrc_bronorganisatie = models.CharField(max_length=9, default='517439943')

    ztc_catalogus_uuid = models.CharField(_('Standaard catalogus UUID'), max_length=36, blank=True)

    ztc_mor_zaaktype_uuid = models.CharField(_('Zaaktype "Melding Openbare Ruimte" UUID'), max_length=36, blank=True)
    ztc_mor_statustype_new_uuid = models.CharField(_('Statustype "Nieuw" UUID'), max_length=36, blank=True)

    class Meta:
        verbose_name = _('Configuratie')

    def get_zdsclient_config(self):
        """
        Returns the ZDSClient configuration format.
        """
        result = {}
        for service in ['zrc', 'drc', 'ztc', 'orc']:
            base_url = getattr(self, '{}_base_url'.format(service))
            if base_url:
                o = urlparse(base_url)
                result[service] = {
                    'host': o.hostname,
                    'port': o.port,
                    'scheme': o.scheme,
                }
        return result
