from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from solo.admin import SingletonModelAdmin

from .models import SiteConfiguration


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(SingletonModelAdmin):
    fieldsets = (
        (_('Algemeen'), {
            'fields': ['google_api_key', ],
        }),
        (_('Zaakregistratiecomponent (ZRC)'), {
            'fields': ['zrc_base_url', 'zrc_bronorganisatie']
        }),
        (_('Documentregistratiecomponent (DRC)'), {
            'fields': ['drc_base_url']
        }),
        (_('Zaaktypecatalogus (ZTC)'), {
            'fields': ['ztc_base_url', 'ztc_catalogus_uuid']
        }),
        (_('Overige registraties component (ORC)'), {
            'fields': ['orc_base_url']
        }),
        (_('Demo applicatie: Melding openbare ruimte'), {
            'fields': ['ztc_mor_zaaktype_uuid', 'ztc_mor_statustype_new_uuid'],
        }),
    )
