import base64
import datetime
import logging
import uuid

from django import forms
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from ..mixins import ZACViewMixin
from ..models import SiteConfiguration, client

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

    bijlage = forms.FileField(
        required=False, help_text='Foto of andere afbeelding die betrekking heeft op de melding.')


class MORCreateView(ZACViewMixin, FormView):
    title = 'Melding Openbare Ruimte'
    subtitle = 'Maak een nieuwe melding'

    template_name = 'demo/mor/mor_create.html'
    form_class = MORCreateForm
    success_url = reverse_lazy('demo:mor-thanks')

    def form_valid(self, form):
        config = SiteConfiguration.get_solo()

        # Haal ZaakType:Melding Openbare Ruimte uit het ZTC
        zaaktype = client('ztc').retrieve(
            'zaaktype',
            catalogus_uuid=config.ztc_catalogus_uuid,
            uuid=config.ztc_mor_zaaktype_uuid,
        )
        # Haal StatusType:Nieuw uit het ZTC
        status_type = client('ztc').list(
            'statustype',
            catalogus_uuid=config.ztc_catalogus_uuid,
            zaaktype_uuid=config.ztc_mor_zaaktype_uuid,
            # uuid=config.ztc_mor_statustype_new_uuid,
        )
        # Haal InformationObjectType:Afbeelding uit het ZTC
        informatieobjecttype = client('ztc').list(
            'informatieobjecttype',
            catalogus_uuid=config.ztc_catalogus_uuid,
            # uuid=config.ztc_mor_informatieobjecttype_image_uuid
        )

        # assert status_type['url'] in zaaktype['statustypen']

        # Verwerk de melding informatie...
        form_data = form.cleaned_data

        # Maak een Zaak aan in het ZRC.
        data = {
            'zaaktype': zaaktype['url'],
            'bronorganisatie': config.zrc_bronorganisatie,
            'registratiedatum': datetime.date.today().isoformat(),
            'toelichting': form_data['toelichting'],
            'startdatum': datetime.date.today().isoformat(),
            # TODO: VerantwoordelijkeOrganisatie...
            'verantwoordelijkeOrganisatie': '245122461',
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

        zaak = client('zrc').create('zaak', data)

        # zaak_id = zaak['url'].rsplit('/')[-1]
        # assert 'url' in zaak

        # Geef de Zaak een status in het ZRC.
        status = client('zrc').create('status', {
            'zaak': zaak[0]['url'],
            'statusType': status_type[0]['url'],
            'datumStatusGezet': datetime.datetime.now().isoformat(),
            'statustoelichting': 'Melding ontvangen',
        })

        # zaak = client('zrc').retrieve('zaak', id=zaak_id)
        # assert zaak['status'] == status['url']

        # # assign address information
        # verblijfsobject = client('orc').create('verblijfsobject', {
        #     'identificatie': uuid.uuid4().hex,
        #     'hoofdadres': {
        #         'straatnaam': 'Keizersgracht',
        #         'postcode': '1015 CJ',
        #         'woonplaatsnaam': 'Amsterdam',
        #         'huisnummer': '117',
        #     }
        # })
        # zaak_object = client('zrc').create('zaakobject', {
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

            eio = client('drc').create('enkelvoudiginformatieobject', {
                # TODO: Dit moet automatisch?
                'identificatie': uuid.uuid4().hex,
                'bronorganisatie': config.zrc_bronorganisatie,
                'creatiedatum': zaak['registratiedatum'],
                'titel': attachment.name,
                'auteur': 'anoniem',
                'formaat': attachment.content_type,
                'taal': 'dut',  # TODO: Why?!
                'inhoud': base64_string,
                'informatieobjecttype': informatieobjecttype['url'],
            })

            # Koppel dit document aan de Zaak in het DRC. De omgekeerde
            # relatie is de verantwoordelijkheid van het DRC.
            oio = client('drc').create('objectinformatieobject', {
                'object': zaak['url'],
                'informatieobject': eio['url'],
                # TODO: Deze enum moet ergens vandaan komen.
                'objectType': 'zaak',
            })

        return super().form_valid(form)


class MORThanksView(ZACViewMixin, TemplateView):
    title = 'Melding Openbare Ruimte'
    subtitle = 'Bedankt voor uw melding'

    template_name = 'demo/mor/mor_thanks.html'

    keep_logs = True
