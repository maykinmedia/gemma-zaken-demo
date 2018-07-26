import base64
import datetime
import logging
import uuid

from django import forms
from django.conf import settings
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView

from zdsclient import ztc_client, zrc_client, drc_client
from zdsclient.client import Log

logger = logging.getLogger(__name__)


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
