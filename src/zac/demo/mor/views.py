import base64
import datetime
import logging
import uuid

from django import forms
from django.conf import settings
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView, TemplateView, FormView
from django.utils.translation import ugettext_lazy as _

from zdsclient import ztc_client, zrc_client, drc_client
from zdsclient.client import Log

logger = logging.getLogger(__name__)


#
# def test_melding_overlast(text_file, png_file):
#     ztc_client = Client('ztc')
#     zrc_client = Client('zrc')
#     orc_client = Client('orc')
#     drc_client = Client('drc')
#
#     # retrieve zaaktype/statustype from ZTC
#     zaaktype = ztc_client.retrieve('zaaktype', catalogus_pk=1, id=1)
#     status_type = ztc_client.retrieve('statustype', catalogus_pk=1, zaaktype_pk=1, id=1)
#     assert status_type['url'] in zaaktype['statustypen']
#
#     # registreer zaak
#     zaak = zrc_client.create('zaak', {
#         'zaaktype': zaaktype['url'],
#         'bronorganisatie': '517439943',
#         'registratiedatum': '2018-06-18',
#         'toelichting': 'Hout van een boot is afgebroken en blokkeert de '
#                        'linkerdoorgang van een brug.',
#         'zaakgeometrie': {
#             'type': 'Point',
#             'coordinates': [
#                 4.910649523925713,
#                 52.37240093589432
#             ]
#         }
#
#     })
#     zaak_id = zaak['url'].rsplit('/')[-1]
#     assert 'url' in zaak
#
#     # set status
#     status = zrc_client.create('status', {
#         'zaak': zaak['url'],
#         'statusType': status_type['url'],
#         'datumStatusGezet': '2018-06-18T15:11:33Z',
#         'statustoelichting': 'Melding ontvangen',
#     })
#
#     zaak = zrc_client.retrieve('zaak', id=zaak_id)
#     assert zaak['status'] == status['url']
#
#     # assign address information
#     verblijfsobject = orc_client.create('verblijfsobject', {
#         'identificatie': uuid.uuid4().hex,
#         'hoofdadres': {
#             'straatnaam': 'Keizersgracht',
#             'postcode': '1015 CJ',
#             'woonplaatsnaam': 'Amsterdam',
#             'huisnummer': '117',
#         }
#     })
#     zaak_object = zrc_client.create('zaakobject', {
#         'zaak': zaak['url'],
#         'object': verblijfsobject['url'],
#     })
#     assert 'url' in zaak_object
#
#     # Upload the files with POST /enkelvoudiginformatieobject (DRC)
#     byte_content = text_file.read()  # text_file comes from pytest fixture
#     base64_bytes = b64encode(byte_content)
#     base64_string = base64_bytes.decode('utf-8')
#
#     text_attachment = drc_client.create('enkelvoudiginformatieobject', {
#         'identificatie': uuid.uuid4().hex,
#         'bronorganisatie': '1',
#         'creatiedatum': zaak['registratiedatum'],
#         'titel': 'text_extra.txt',
#         'auteur': 'anoniem',
#         'formaat': 'text/plain',
#         'taal': 'nl',
#         'inhoud': base64_string
#     })
#
#     # Test if the EnkelvoudigInformatieObject stored has the right information
#     assert 'creatiedatum' in text_attachment
#     assert text_attachment['creatiedatum'] == zaak['registratiedatum']
#
#     # Retrieve the EnkelvoudigInformatieObject
#     txt_object_id = text_attachment['url'].rsplit('/')[-1]
#     text_attachment = drc_client.retrieve('enkelvoudiginformatieobject', id=txt_object_id)
#
#     # Test if the attached filed is our initial file
#     assert requests.get(text_attachment['inhoud']).content == byte_content
#
#     byte_content = png_file.getvalue()
#     base64_bytes = b64encode(byte_content)
#     base64_string = base64_bytes.decode('utf-8')
#
#     image_attachment = drc_client.create('enkelvoudiginformatieobject', {
#         'identificatie': uuid.uuid4().hex,
#         'bronorganisatie': '1',
#         'creatiedatum': zaak['registratiedatum'],
#         'titel': 'afbeelding.png',
#         'auteur': 'anoniem',
#         'formaat': 'image/png',
#         'taal': 'nl',
#         'inhoud': base64_string
#     })
#
#     # Link the files to a 'Zaak' with POST /zaakinformatieobjecten (ZRC)
#     zaakinformatieobject_1 = drc_client.create('zaakinformatieobject', {
#         'zaak': zaak['url'],
#         'informatieobject': text_attachment['url'],
#     })
#     assert 'url' in zaakinformatieobject_1
#
#     zaakinformatieobject_2 = drc_client.create('zaakinformatieobject', {
#         'zaak': zaak['url'],
#         'informatieobject': image_attachment['url'],
#     })
#     informatie_object_id = zaakinformatieobject_2['url'].rsplit('/')[-1]
#
#     # Test if it's possible to retrieve ZaakInformatieObject
#     some_informatie_object = drc_client.retrieve('zaakinformatieobject', id=informatie_object_id)
#
#     # Retrieve the EnkelvoudigInformatieObject from ZaakInformatieObject
#     assert 'informatieobject' in some_informatie_object
#
#     img_object_id = some_informatie_object['informatieobject'].rsplit('/')[-1]
#     image_attachment = drc_client.retrieve('enkelvoudiginformatieobject', id=img_object_id)
#
#     # Test if image correspond to our initial image
#     assert requests.get(image_attachment['inhoud']).content == byte_content


class MORCreateForm(forms.Form):
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput)
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput)

    uw_naam = forms.CharField(required=False)
    uw_email_adres = forms.EmailField(label='Uw e-mail adres', required=False)
    blijf_op_de_hoogte = forms.BooleanField(required=False)

    adres = forms.CharField(required=False, label='Adres van de melding',
                            help_text='Adres of omschrijving van de locatie waar de melding over gaat.')
    toelichting = forms.CharField(widget=forms.Textarea)

    bijlage = forms.FileField(required=False, help_text='Foto of andere afbeelding die betrekking heeft op de melding.')


class MORCreateView(FormView):
    title = 'Melding Openbare Ruimte'
    subtitle = 'Maak een nieuwe melding'

    template_name = 'demo/mor/mor_create.html'
    form_class = MORCreateForm
    success_url = reverse_lazy('demo:mor-thanks')

    def form_invalid(self, form):
        return super().form_invalid(form)

    def form_valid(self, form):
        Log.clear()

        # Haal ZaakType en StatusType op uit het ZTC.
        zaaktype = ztc_client.retrieve(
            'zaaktype',
            catalogus_uuid=settings.DEMO_ZTC_CATALOGUS_UUID,
            uuid=settings.DEMO_MOR_ZTC_ZAAKTYPE_UUID
        )  # Nieuw
        status_type = ztc_client.retrieve(
            'statustype',
            catalogus_uuid=settings.DEMO_ZTC_CATALOGUS_UUID,
            zaaktype_uuid=settings.DEMO_MOR_ZTC_ZAAKTYPE_UUID,
            uuid=settings.DEMO_MOR_ZTC_STATUSTYPE_NEW_UUID
        )
        # assert status_type['url'] in zaaktype['statustypen']

        # Verwerk de melding informatie...
        form_data = form.cleaned_data

        # Maak een Zaak aan in het ZRC.
        data = {
            'zaaktype': zaaktype['url'],
            'bronorganisatie': settings.DEMO_BRONORGANISATIE,
            'registratiedatum': datetime.date.today().isoformat(),
            'toelichting': form_data['toelichting'],
        }

        if form_data['longitude'] and form_data['latitude']:
            data.update({
                'zaakgeometrie': {
                    'type': 'Point',
                    'coordinates': [
                        form_data['longitude'],
                        form_data['latitude'],
                    ]
                }
            })

        zaak = zrc_client.create('zaak', data)

        # zaak_id = zaak['url'].rsplit('/')[-1]
        # assert 'url' in zaak

        # Geef de Zaak een status in het ZRC.
        status = zrc_client.create('status', {
            'zaak': zaak['url'],
            'statusType': status_type['url'],
            'datumStatusGezet': datetime.datetime.now().isoformat(),
            'statustoelichting': 'Melding ontvangen',
        })

        # zaak = zrc_client.retrieve('zaak', id=zaak_id)
        # assert zaak['status'] == status['url']

        # # assign address information
        # verblijfsobject = orc_client.create('verblijfsobject', {
        #     'identificatie': uuid.uuid4().hex,
        #     'hoofdadres': {
        #         'straatnaam': 'Keizersgracht',
        #         'postcode': '1015 CJ',
        #         'woonplaatsnaam': 'Amsterdam',
        #         'huisnummer': '117',
        #     }
        # })
        # zaak_object = zrc_client.create('zaakobject', {
        #     'zaak': zaak['url'],
        #     'object': verblijfsobject['url'],
        # })
        # assert 'url' in zaak_object

        # Maak een document aan in het DMC.
        if form_data['bijlage']:
            attachment = form_data['bijlage']

            byte_content = form_data['bijlage'].read()
            base64_bytes = base64.b64encode(byte_content)
            base64_string = base64_bytes.decode('utf-8')

            eio = drc_client.create('enkelvoudiginformatieobject', {
                # TODO: Dit moet automatisch?
                'identificatie': uuid.uuid4().hex,
                'bronorganisatie': settings.DEMO_BRONORGANISATIE,
                'creatiedatum': zaak['registratiedatum'],
                'titel': attachment.name,
                'auteur': 'anoniem',
                'formaat': attachment.content_type,
                'taal': 'nl',  # TODO: Why?!
                'inhoud': base64_string
            })

            # Koppel dit document aan de Zaak in het DMC
            # TODO: Dit moet (ook) omgekeerd, in het ZRC leven.
            zio = drc_client.create('zaakinformatieobject', {
                'zaak': zaak['url'],
                'informatieobject': eio['url'],
            })

        return super().form_valid(form)


class MORThanksView(TemplateView):
    title = 'Melding Openbare Ruimte'
    subtitle = 'Bedankt voor uw melding'

    template_name = 'demo/mor/mor_thanks.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'log_entries': Log.entries()
        })
        return context




#
#
# class VergunningsAanvraagPreview(UpdateView):
#     model = VergunningsAanvraag
#     template_name_suffix = '_preview'
#     fields = []
#
#     def form_valid(self, form):
#         self.object.zaakstatus = ZaakStatus.in_behandeling
#         self.object.save()
#
#         return super().form_valid(form)
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context.update({
#             'ZaakStatus': ZaakStatus,
#         })
#         return context
#
#     def get_success_url(self):
#         return reverse('demo:update', kwargs={'pk': self.object.pk})
#
#
# class VergunningsAanvraagUpdate(UpdateView):
#     model = VergunningsAanvraag
#     template_name_suffix = '_update'
#     fields = ['zaakstatus', ]
#
#     def form_valid(self, form):
#         messages.add_message(self.request, messages.INFO, _('Aanvraag is {}.'.format(form.instance.get_zaakstatus_display())))
#
#         return super().form_valid(form)
#
#     def get_context_data(self, **kwargs):
#         try:
#             # Retrieve Kadaster data.
#             kadaster_data = kadaster_client.get(
#                 self.object.lokatie_postcode,
#                 '{}{}'.format(self.object.lokatie_huisnummer_toevoeging, self.object.lokatie_huisnummer),
#                 city_name=self.object.lokatie_plaats,
#                 # This is the most important part: Specify which process step is performed here. The ID is taken from the
#                 # Verwerkingsregister.
#                 process_id=1,
#             )
#         except Exception as e:
#             logger.exception(e)
#             kadaster_data = {}
#
#         context = super().get_context_data(**kwargs)
#         context.update({
#             'kadaster_data': kadaster_data,
#             'kadaster_href': kadaster_data['_links']['self']['href'] if kadaster_data else '',
#             'GOOGLE_API_KEY': settings.GOOGLE_API_KEY,
#             'ZaakStatus': ZaakStatus,
#         })
#
#         return context
#
#     def get_success_url(self):
#         return reverse('demo:list')
