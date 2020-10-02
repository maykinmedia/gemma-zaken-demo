from django.contrib import admin, messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from solo.admin import SingletonModelAdmin
from vng_api_common.notifications.constants import (
    SCOPE_NOTIFICATIES_CONSUMEREN_LABEL
)
from vng_api_common.notifications.models import (
    NotificationsConfig, Subscription
)
from zds_client import ClientAuth

from zac.demo.mijngemeente.models import UserNotification

from .models import OtherZTC, SiteConfiguration


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    pass


class OtherZTCInline(admin.TabularInline):
    model = OtherZTC
    extra = 1


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
            'description': _('Dit betreft de "hoofd"-ZTC. Andere ZTC\'s kunnen onderaan worden toegevoegd.'),
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
        (_('Notificatie component (NC)'), {
            'description': _('Om te abonneren op notificaties moet een NC bekend zijn.'),
            'fields': [
                'nc_base_url',
                'nc_client_id',
                'nc_secret',
            ]
        }),
        (_('Notificaties ontvangen'), {
            'description': _('Deze demo applicatie kan notificaties ontvangen.'),
            'fields': [
                # 'nc_method',
                'callback_url',
                'get_example_callback_url',
                'callback_client_id',
                'callback_secret',
                'get_callback_jwt',
                # 'nc_amqp_host',
                # 'nc_amqp_port',
            ]
        }),
        (_('Basis registratie (ingeschreven) personen (BRP)'), {
            'fields': [
                'brp_base_url',
                'brp_api_key',
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
        (_('Objects and objecttypes'), {
            'fields': [
                'objects_api',
                'objecttypes_api',
            ]
        })

    )
    inlines = [OtherZTCInline, ]
    readonly_fields = ['get_example_callback_url', 'get_callback_jwt']
    raw_id_fields = ('objects_api', 'objecttypes_api')

    def get_example_callback_url(self, obj):
        return 'http(s)://<domain>{}'.format(
            reverse('demo:mijngemeente-notificaties-webhook')
        )
    get_example_callback_url.short_description = _('Callback URL voorbeeld')
    get_example_callback_url.help_text = _('De URL naar de callback API van deze demo applicatie. Hier stuurt het NC '
                                           'zijn notificaties heen.')

    def get_callback_jwt(self, obj):
        if not obj.callback_client_id or not obj.callback_secret:
            return ''
        auth = ClientAuth(
            client_id=obj.callback_client_id,
            secret=obj.callback_secret,
            scopes=[
                SCOPE_NOTIFICATIES_CONSUMEREN_LABEL
            ]
        )
        return auth.credentials()['Authorization']
    get_callback_jwt.short_description = _('Callback JWT')
    get_callback_jwt.help_text = _('De JWT die het NRC moet gebruiken om van de callback API van deze demo applicatie '
                                   'gebruik te mogen maken.')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        subscription = Subscription.objects.first()
        if subscription and not subscription._subscription and request.method == 'GET':
            messages.warning(request, mark_safe(_(
                'Notificaties zijn nog niet volledig geconfigureerd: <a href="{}">Registreer de webhook bij het NRC</a>.'
            ).format(reverse('admin:notifications_subscription_changelist'))))

        return super().change_view(request, object_id, form_url, extra_context)


admin.site.unregister(NotificationsConfig)
# admin.site.unregister(Subscription)
# admin.site.unregister(APICredential)
