from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

import requests
from vng_api_common.notifications.models import Subscription
from zds_client import ClientError

from zac.demo.models import SiteConfiguration, client


def _can_connect(service, url):
    try:
        response = requests.get(url, timeout=1)
    except Exception:
        return False, _('Server onbereikbaar')

    if response.status_code != 200:
        return False, _('Server geeft een error')

    return True, None


def _can_auth(service, url):
    try:
        response = requests.get(url, timeout=1)
    except Exception:
        return False, _('Server onbereikbaar')

    if response.status_code != 200:
        return False, _('Server geeft een error')

    data = response.json()
    k, v = list(data.items())[0]

    c = client(service)

    try:
        response = c.retrieve(None, v)
    except ClientError as e:
        try:
            # Exception for ZRC. The 412 error means we at least were autorised.
            if service == 'zrc' and e.args[0]['status'] == 412:
                return True, None
            return False, e.args[0]['title']
        except Exception:
            return False, str(e)
    except Exception as e:
        return False, str(e)

    return True, None


def _get_general_config(config):
    # google_maps_api_key_status = False
    # if config.google_maps_api_key:
    #     res = requests.get('https://maps.googleapis.com/maps/api/staticmap?size=10x10&key={config.google_maps_api_key}')
    #     google_maps_api_key_status = res.status_code == 200

    google_maps_center = (config.google_maps_lat, config.google_maps_long)

    catalogus_msg = None
    try:
        ztc_client = client('ztc')
        catalogus = ztc_client.retrieve(
            'catalogus',
            uuid=config.ztc_catalogus_uuid
        )
    except ClientError as e:
        try:
            catalogus_msg = e.args[0]['title']
        except Exception:
            catalogus_msg = str(e)
    except Exception as e:
        catalogus_msg = str(e)

    return [
        (
            _('Google Maps API-key'),
            config.google_maps_api_key,
            bool(config.google_maps_api_key),
            None,
        ),
        (
            _('Google Maps standaard locatie'),
            ', '.join(map(str, google_maps_center)),
            True,
            None,
        ),
        (
            _('Standaard ZTC Catalogus UUID'),
            config.ztc_catalogus_uuid,
            not bool(catalogus_msg),
            catalogus_msg
        ),
    ]


def _get_api_config(config, service, url):
    service_config = config.get_service_config(service)

    conn_success, conn_msg = _can_connect(service, url)
    auth_success, auth_msg = _can_auth(service, url)

    return [
        (
            _('Basis URL'),
            service_config.base_url,
            conn_success,
            conn_msg
        ),
        (
            _('Client ID'),
            service_config.client_id,
            auth_success,
            None
        ),
        (
            _('Secret'),
            '{}***{}'.format(service_config.secret[0], service_config.secret[-1]) if service_config.secret else '',
            auth_success,
            auth_msg
        ),
    ]


def _get_mijn_gemeente_config(config):
    subscriptions = list(Subscription.objects.filter(_subscription__startswith=config.nc_base_url))
    if len(subscriptions) == 0:
        msg = _('Geen abonnement op kanaal "zaken"')
    elif len(subscriptions) > 1:
        msg = _('Meerdere abonnementen gevonden')
    elif 'zaken' not in subscriptions[0].channels:
        msg = _('Abonnement gevonden maar niet op kanaal "zaken"')
    elif Subscription.objects.exclude(_subscription__startswith=config.nc_base_url):
        msg = _('Abonnement gevonden bij ander NRC dan geconfigureerd')
    else:
        msg = None

    return [
        (
            _('Abonnement op kanaal "zaken"'),
            subscriptions[0]._subscription if not msg else '',
            not bool(msg),
            msg
        ),
    ]


def _get_mor_config(config):
    ztc_client = client('ztc')

    zaaktype = None
    statustype = None
    informatieobjecttype = None

    ztc_msg = ''
    try:
        zaaktype = ztc_client.retrieve(
            'zaaktype',
            catalogus_uuid=config.ztc_catalogus_uuid,
            uuid=config.ztc_mor_zaaktype_uuid
        )
        statustype = ztc_client.retrieve(
            'statustype',
            catalogus_uuid=config.ztc_catalogus_uuid,
            zaaktype_uuid=config.ztc_mor_zaaktype_uuid,
            uuid=config.ztc_mor_statustype_new_uuid,
        )
        informatieobjecttype = ztc_client.retrieve(
            'informatieobjecttype',
            catalogus_uuid=config.ztc_catalogus_uuid,
            uuid=config.ztc_mor_informatieobjecttype_image_uuid
        )
    except ClientError as e:
        try:
            ztc_msg = e.args[0]['title']
        except Exception:
            ztc_msg = str(e)
    except Exception as e:
        ztc_msg = str(e)

    return [
        (
            _('Bron organisatie'),
            config.zrc_bronorganisatie,
            bool(config.zrc_bronorganisatie),
            None
        ),
        (
            _('Zaaktype "Melding openbare ruimte" UUID'),
            config.ztc_mor_zaaktype_uuid,
            zaaktype is not None,
            ztc_msg if zaaktype is None else None,
        ),
        (
            _('Statustype "Nieuw" UUID'),
            config.ztc_mor_statustype_new_uuid,
            statustype is not None,
            ztc_msg if statustype is None else None
        ),
        (
            _('Informatieobjecttype "Afbeelding" UUID'),
            config.ztc_mor_informatieobjecttype_image_uuid,
            informatieobjecttype is not None,
            ztc_msg if informatieobjecttype is None else None
        ),
    ]


class ConfigView(TemplateView):
    template_name = 'config/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        config = SiteConfiguration.get_solo()
        services = config.get_services()

        groups = []

        groups.extend([
            (_('Algemeen'), _get_general_config(config)),
            (_('Demo applicatie: Mijn Gemeente'), _get_mijn_gemeente_config(config)),
            (_('Demo applicatie: Melding Openbare Ruimte'), _get_mor_config(config)),
        ])

        for service, url in services.items():
            groups.append(
                (service.upper(), _get_api_config(config, service, url))
            )

        context.update({
            'groups': groups
        })

        return context
