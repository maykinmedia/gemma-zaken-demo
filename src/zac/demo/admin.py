from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from solo.admin import SingletonModelAdmin

from .models import SiteConfiguration


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(SingletonModelAdmin):
    fieldsets = (
        (_('Algemeen'), {
            'fields': [
                'global_api_client_id',
                'global_api_secret',
                'google_maps_api_key',
                'google_maps_lat',
                'google_maps_long',
            ],
        }),
        (_('Zaak registratie component (ZRC)'), {
            'fields': [
                'zrc_base_url',
                'zrc_client_id',
                'zrc_secret',
            ]
        }),
        (_('Document registratie component (DRC)'), {
            'fields': [
                'drc_base_url',
                'drc_client_id',
                'drc_secret',
            ]
        }),
        (_('Zaaktype catalogus (ZTC)'), {
            'fields': [
                'ztc_base_url',
                'ztc_client_id',
                'ztc_secret',
                'ztc_catalogus_uuid',
            ]
        }),
        (_('Besluit registratie component (BRC)'), {
            'fields': [
                'brc_base_url',
                'brc_client_id',
                'brc_secret',
            ]
        }),
        (_('Overige registraties component (ORC)'), {
            'fields': [
                'orc_base_url',
                'orc_client_id',
                'orc_secret',
            ]
        }),
        (_('Demo applicatie: Melding openbare ruimte'), {
            'fields': [
                'zrc_bronorganisatie',
                'ztc_mor_zaaktype_uuid',
                'ztc_mor_statustype_new_uuid',
                'ztc_mor_informatieobjecttype_image_uuid',
            ]
        }),
    )
