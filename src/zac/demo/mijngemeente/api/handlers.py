import logging

import isodate
from django.urls import reverse

from zac.demo.models import client
from zac.demo.utils import get_uuid

from ..models import UserNotification

logger = logging.getLogger(__name__)


class StoreAndPublishHandler:
    """
    Combination of storing notification in the database (typically for when the
    frontend is not shown) but also sends a notification to the frontend via
    websockets.
    """

    def handle(self, message: dict) -> None:
        # TODO: Add to queue, let a worker process the notifications, etc...
        # For now, we process the incomming notification immediately and create
        # a "user" notification synchronously with the incomming call.
    
        channel = message['kanaal']
        main_object = message['hoofd_object']
        resource = message['resource']
        resource_url = message['resource_url']
        action = message['actie']
        kenmerken = message['kenmerken']  # Unused
    
        # Advanced businesslogic :)
        #
        # We do 3 scenario's in detail, the other scenario's give a generic
        # message. In reality, you can also stack notifications in one message
        # or do other fancy stuff.
        if channel == 'zaken' and action == 'create' and resource in ['zaak', 'status', 'zaakinformatieobject']:
            zrc_client = client('zrc')
    
            zaak = zrc_client.retrieve('zaak', url=main_object)
            zaak_uuid = get_uuid(zaak['url'])
    
            ztc_client = client('ztc', url=zaak['zaaktype'])
            zaak_type = ztc_client.retrieve('zaaktype', url=zaak['zaaktype'])
    
            msg_reference = zaak['identificatie']
            msg_url = reverse('demo:zaakbeheer-detail', kwargs={'uuid': zaak_uuid})

            # 1. Zaak aanmaken
            if resource == 'zaak':
                try:
                    _doorlooptijd_dagen = isodate.parse_duration(zaak_type['doorlooptijd']).days
                    doorlooptijd = 'binnen {} dagen'.format(_doorlooptijd_dagen)
                except:
                    doorlooptijd = 'binnenkort'

                msg_title = 'Zaak <strong>{}</strong> aangemaakt.'.format(zaak_type['onderwerp'])
                msg_body = 'Naar aanleiding van uw <strong>{}</strong> gaat de behandelaar deze zaak <strong>{}' \
                           '</strong>. U kunt <strong>{}</strong> een opvolging ' \
                       'verwachten. Bedankt voor het <strong>{}</strong>.'.format(
                            zaak_type['aanleiding'].lower(),
                            zaak_type['handelingBehandelaar'].lower(),
                            doorlooptijd,
                            zaak_type['handelingInitiator'].lower(),
                        )
    
            # 2. Status wijziging bij Zaak
            elif resource == 'status':
                # Sanity check could be done here...
                # assert zaak['status'] == resource_url
    
                status = zrc_client.retrieve('status', url=resource_url)
                status_type = ztc_client.retrieve('statustype', url=status['statustype'])
    
                # TODO: Attribute "informeren" is not part of the ZTC API yet...
                if not status_type.get('informeren', True):
                    logger.info('Statustype should not be communicated to initiator.')
                    return
    
                msg_title = 'Zaak {} gewijzigd.'.format(zaak_type['onderwerp'])
                msg_body = 'De status van uw zaak is gewijzigd naar: {}. {} {}'.format(
                    status_type['omschrijving'],
                    status_type['statustekst'],
                    'Toelichting: {}'.format(status['statustoelichting'])if status['statustoelichting'] else ''
                )
    
            # 3. Document toegevoegd aan Zaak
            #
            # Funny thing is that we don't need a subscription on the DRC for
            # this. The relation is also created on the ZRC-side.
            elif resource == 'zaakinformatieobject':
                # TODO: Does this work? I don't see a "read" URL for a relation...
    
                drc_client = client('drc', url=resource_url)
                informatieobject = drc_client.retrieve('enkelvoudiginformatieobject', url=resource_url)
                informatieobjecttype = ztc_client.retrieve(informatieobject['informatieobjecttype'])
    
                msg_title = 'Zaak {} gewijzigd.'.format(zaak_type['onderwerp'])
                msg_body = 'Er is een {} toegevoegd aan uw zaak met de titel "{}".'.format(
                    informatieobjecttype['omschrijving'] or 'document',
                    informatieobject['titel'],
                )
            else:
                raise NotImplemented()
    
        else:
            # Generic message handling...
            channel_mapping = {
                'zaken': 'zaak',
                'documenten': 'document'
            }
            channel_text = channel_mapping.get(channel, channel)
    
            action_mapping = {
                'create': 'aangemaakt',
                'update': 'gewijzigd',
                'partial_update': 'gewijzigd',
                'destroy': 'verwijderd',
    
                # These will probably not exist.
                'read': 'opgevraagd',
                'list': 'voorgekomen in resultaten',
            }
    
            # If the main resources changed, we construct a slightly different
            # title.
            if resource in ['zaak', 'document']:
                title_action_text = action_mapping.get(action, f'"heeft {action}" uitgevoerd')
                msg_body = ''
            else:
                title_action_text = 'gewijzigd'
                resource_action_text = action_mapping.get(action, action)
                msg_body = f'{resource.title()} {resource_action_text} bij de {channel_text}.'
    
            try:
                short_uuid = get_uuid(main_object)[:10]
            except:
                short_uuid = '???'
    
            # Assign generic message variables.
            msg_title = f'{channel_text.title()} {title_action_text}'
            msg_reference = f'{channel_text.upper()}-{short_uuid}'
            msg_url = resource_url or main_object  # For debugging, the URL to the object in the API.
    
        # Create message locally.
        kwargs = {
            'title': msg_title,
            'body': msg_body,
            'reference': msg_reference,
            'url': msg_url,
        }
    
        UserNotification.create_and_notify(**kwargs)


default = StoreAndPublishHandler()
