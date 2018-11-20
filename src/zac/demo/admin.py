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
        (_('Zaak registratie component (ZRC)'), {
            'fields': [
                'zrc_base_url',
                'zrc_bronorganisatie'
            ]
        }),
        (_('Document registratie component (DRC)'), {
            'fields': ['drc_base_url']
        }),
        (_('Zaaktype catalogus (ZTC)'), {
            'fields': [
                'ztc_base_url',
                'ztc_catalogus_uuid'
            ]
        }),
        (_('Besluit registratie component (BRC)'), {
            'fields': ['brc_base_url']
        }),
        (_('Overige registraties component (ORC)'), {
            'fields': ['orc_base_url']
        }),
        (_('Demo applicatie: Melding openbare ruimte'), {
            'fields': [
                'ztc_mor_zaaktype_uuid',
                'ztc_mor_statustype_new_uuid',
                'ztc_mor_informatieobjecttype_image_uuid',
            ]
        }),
    )
