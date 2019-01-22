import copy
import datetime
import logging

import requests
from django import forms
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import FormView, TemplateView

from zds_client.client import ClientError, Client

from ..mixins import ZACViewMixin
from ..models import SiteConfiguration, client
from ..utils import api_response_list_to_dict, isodate

logger = logging.getLogger(__name__)


def get_uuid(url, index=-1):
    return url.split('/')[index]


class ZaakListView(ZACViewMixin, TemplateView):
    title = 'Zaakbeheer'
    subtitle = 'Lijst van Zaken uit het ZRC'
    template_name = 'demo/zaakbeheer/zaak_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        config = SiteConfiguration.get_solo()

        # Retrieve all Zaken
        zaken = client('zrc').list('zaak')

        # TODO: Workaround: The status should be done with embedding when
        # requesting a list of Zaken.
        statusses_by_url = api_response_list_to_dict(
            client('zrc').list('status')
        )

        # Retrieve a list of all ZaakTypen from the "main" ZTC
        zaaktypen = client('ztc').list('zaaktype', catalogus_uuid=config.ztc_catalogus_uuid)
        zaaktypes_by_url = api_response_list_to_dict(zaaktypen)

        # Retrieve a list of StatusTypen from the "main" ZTC.
        # TODO: Workaround: We cannot get a full list of all StatusTypes, so we
        # make a call for each Zaaktype, to get the available Statustypes.
        statustypen = []
        for zaaktype in zaaktypen:
            # Workaround: UUID is not part of the serialiser yet, otherwise it was simply: zaaktype['uuid']
            statustypen += client('ztc').list('statustype', catalogus_uuid=config.ztc_catalogus_uuid, zaaktype_uuid=get_uuid(zaaktype['url']))
        statustypen_by_url = dict([
            (statustype['url'], statustype) for statustype in statustypen
        ])

        # Construct template vars.
        headers = [
            '#',
            'Bronorganisatie',
            'Type',
            'Status (type)',
            'Status toelichting',
            'Registratiedatum'
        ]
        rows = []
        for index, zaak in enumerate(zaken):
            zaaktype = zaaktypes_by_url.get(zaak['zaaktype'])

            # If the ZaakType is not in the "main" ZTC, retrieve it manually.
            if zaaktype is None:
                zaaktype = client('ztc', url=zaak['zaaktype']).retrieve('zaaktype', url=zaak['zaaktype'])

                # Skip over Zaak with unknown Zaaktype.
                if zaaktype is None:
                    continue

            status = statusses_by_url.get(zaak['status'])
            statustype = None
            if status:
                statustype = statustypen_by_url.get(status['statusType'])

                # If the StatusType is not in the "main" ZTC, retrieve it
                # manually.
                if statustype is None:
                    statustype = client('ztc', url=status['statusType']).retrieve('statustype', url=status['statusType'])

            detail_url = reverse('demo:zaakbeheer-detail', kwargs={'uuid': get_uuid(zaak['url'])})

            rows.append([
                mark_safe('<a href="{}">{}</a>'.format(detail_url, index + 1)),
                zaak['bronorganisatie'],
                zaaktype['omschrijving'] if zaaktype else '(onbekend)',
                statustype['omschrijving'] if statustype else '(onbekend)',
                status['statustoelichting'] if status else '(onbekend)',
                zaak['registratiedatum'],
            ])

        context.update({
            'header': headers,
            'rows': rows,
        })

        return context


class ZaakForm(forms.Form):
    zaak_url = forms.CharField(widget=forms.HiddenInput)
    zaaktype = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    identificatie = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    bronorganisatie = forms.CharField()
    registratiedatum = forms.DateField()
    toelichting = forms.CharField(widget=forms.Textarea, required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput, required=False)
    latitude = forms.FloatField(widget=forms.HiddenInput, required=False)


class ZaakDetailView(ZACViewMixin, FormView):
    title = 'Zaakbeheer'
    subtitle = 'Details van een Zaak uit het ZRC'
    template_name = 'demo/zaakbeheer/zaak_detail.html'
    form_class = ZaakForm

    def _pre_dispatch(self, request, *args, **kwargs):
        self.config = SiteConfiguration.get_solo()

        # Haal Zaak op uit ZRC
        zaak = client('zrc').retrieve('zaak', uuid=self.kwargs.get('uuid'))
        self.zaak = zaak
        self.zaak_uuid = get_uuid(self.zaak['url'])

        # Work with any configured ZTC.
        self.ztc_client = client('ztc', url=self.zaak['zaaktype'])
        # TODO: Make a nicer way to get the catalogus UUID.
        self.catalogus_uuid = get_uuid(self.zaak['zaaktype'], -3)

    def get_success_url(self):
        return '{}?keep-logs=true'.format(
            reverse('demo:zaakbeheer-detail', kwargs={'uuid': self.kwargs.get('uuid')})
        )

    def form_valid(self, form):
        form_data = form.cleaned_data

        # Update the Zaak in the ZRC
        client('zrc').partial_update('zaak', uuid=self.zaak_uuid, data={
            'toelichting': form_data['toelichting']
        })

        messages.add_message(self.request, messages.SUCCESS, 'Zaak succesvol bijgewerkt.')

        return super().form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        # Haal Zaaktype op.
        zaaktype = None
        if self.zaak['zaaktype']:
            zaaktype = self.ztc_client.retrieve('zaaktype', url=self.zaak['zaaktype'])

        if 'initial' in form_kwargs:
            extra_initial = copy.deepcopy(self.zaak)
            extra_initial.update({
                'zaak_url': self.zaak['url'],
                'zaaktype': zaaktype['omschrijving'] if zaaktype else '(onbekend)',
            })

            # Extract longitude/latitude from zaakgeometrie if present.
            if self.zaak['zaakgeometrie'] and \
                    self.zaak['zaakgeometrie'].get('type', '').upper() == 'POINT' and \
                    len(self.zaak['zaakgeometrie'].get('coordinates', [])) == 2:

                extra_initial.update({
                    'longitude': self.zaak['zaakgeometrie']['coordinates'][0],
                    'latitude': self.zaak['zaakgeometrie']['coordinates'][1],
                })
            form_kwargs['initial'].update(extra_initial)

        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Retrieve a list of Status (this is possible because we need the types
        # for just this Zaak of a certain ZaakType).
        status_list = client('zrc').list('status', query_params={'zaak': self.zaak['url']})
        statustypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('statustype', catalogus_uuid=self.catalogus_uuid, zaaktype_uuid=get_uuid(self.zaak['zaaktype']))
        )
        # Amend the resulting besluiten with their respective type.
        for status in status_list:
            status['statusType_embedded'] = statustypes_by_url.get(status['statusType'], None)

        # Retrieve a list of EnkelvoudigInformatieObject
        #
        # Look at the relation from the DRC-perspective to include documents
        # linked to Besluiten as well. Skip InformatieObjectType for now as I
        # don't see any use for it.
        document_relation_list = client('drc').list('objectinformatieobject', query_params={'object': self.zaak['url']})
        document_list = []
        for dr in document_relation_list:
            try:
                document = client('drc').retrieve('enkelvoudiginformatieobject', uuid=get_uuid(dr['informatieobject']))
            except ClientError as e:
                logger.exception(e)
                continue
            document_list.append(document)

        # Retrieve a list of Besluiten
        besluit_list = client('brc').list('besluit', query_params={'zaak': self.zaak['url']})
        besluittypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('besluittype', catalogus_uuid=self.catalogus_uuid)
        )
        # Amend the resulting besluiten with their respective type.
        for besluit in besluit_list:
            besluit['besluittype_embedded'] = besluittypes_by_url.get(besluit['besluittype'], None)

        context.update({
            'zaak_uuid': self.zaak_uuid,
            'status_list': status_list,
            'document_list': document_list,
            'besluit_list': besluit_list,
        })
        return context


class StatusForm(forms.Form):
    statustype_url = forms.ChoiceField(label='Status')
    toelichting = forms.CharField()

    def __init__(self, *args, **kwargs):
        status_choices = kwargs.pop('status_choices')

        super().__init__(*args, **kwargs)

        self.fields['statustype_url'].choices = status_choices


class StatusCreateView(ZACViewMixin, FormView):
    title = 'Zaakbeheer - Statussen'
    subtitle = 'Status beheren van deze zaak'
    template_name = 'demo/zaakbeheer/zaakstatus_create.html'
    form_class = StatusForm

    def _pre_dispatch(self, request, *args, **kwargs):
        self.config = SiteConfiguration.get_solo()

        # Retrieve Zaak from ZRC
        zaak = client('zrc').retrieve('zaak', uuid=self.kwargs.get('uuid'))
        self.zaak = zaak
        self.zaak_uuid = get_uuid(self.zaak['url'])

        # Work with any configured ZTC.
        self.ztc_client = client('ztc', url=self.zaak['zaaktype'])
        # TODO: Make a nicer way to get the catalogus UUID.
        self.catalogus_uuid = get_uuid(self.zaak['zaaktype'], -3)

    def get_success_url(self):
        return '{}?keep-logs=true'.format(
            reverse('demo:zaakbeheer-statuscreate', kwargs={'uuid': self.kwargs.get('uuid')})
        )

    def form_valid(self, form):
        form_data = form.cleaned_data

        # Create the Status in the ZRC
        status = client('zrc').create('status', {
            'zaak': self.zaak['url'],
            'statusType': form_data['statustype_url'],
            'datumStatusGezet': datetime.datetime.now().isoformat(),
            'statustoelichting': form_data['toelichting'],
        })

        messages.add_message(self.request, messages.SUCCESS, 'Status succesvol toegevoegd.')

        return super().form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        # Retrieve available StatusTypes of this ZaakType in the ZTC
        statustypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('statustype', catalogus_uuid=self.catalogus_uuid, zaaktype_uuid=get_uuid(self.zaak['zaaktype']))
        )
        statustype_choices = [(url, obj['omschrijving']) for url, obj in statustypes_by_url.items()]

        form_kwargs.update({
            'status_choices': statustype_choices
        })

        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Retrieve a list of Status (this is possible because we need the types
        # for just this Zaak of a certain ZaakType).
        status_list = client('zrc').list('status', query_params={'zaak': self.zaak['url']})
        statustypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('statustype', catalogus_uuid=self.catalogus_uuid, zaaktype_uuid=get_uuid(self.zaak['zaaktype']))
        )
        # Amend the resulting besluiten with their respective type.
        for status in status_list:
            status['statusType_embedded'] = statustypes_by_url.get(status['statusType'], None)

        context.update({
            'zaak_uuid': self.zaak_uuid,
            'status_list': status_list,
        })
        return context


class BesluitForm(forms.Form):
    besluittype_url = forms.ChoiceField(label='Besluit')
    toelichting = forms.CharField()

    def __init__(self, *args, **kwargs):
        besluit_choices = kwargs.pop('besluit_choices')

        super().__init__(*args, **kwargs)

        self.fields['besluittype_url'].choices = besluit_choices


class BesluitCreateView(ZACViewMixin, FormView):
    title = 'Zaakbeheer - Besluiten'
    subtitle = 'Besluiten beheren van deze zaak'
    template_name = 'demo/zaakbeheer/besluit_create.html'
    form_class = BesluitForm

    def _pre_dispatch(self, request, *args, **kwargs):
        self.config = SiteConfiguration.get_solo()

        # Retrieve Zaak from ZRC
        zaak = client('zrc').retrieve('zaak', uuid=self.kwargs.get('uuid'))
        self.zaak = zaak
        self.zaak_uuid = get_uuid(self.zaak['url'])

        # Work with any configured ZTC.
        self.ztc_client = client('ztc', url=self.zaak['zaaktype'])
        # TODO: Make a nicer way to get the catalogus UUID.
        self.catalogus_uuid = get_uuid(self.zaak['zaaktype'], -3)

    def get_success_url(self):
        return '{}?keep-logs=true'.format(
            reverse('demo:zaakbeheer-besluitcreate', kwargs={'uuid': self.kwargs.get('uuid')})
        )

    def form_valid(self, form):
        form_data = form.cleaned_data

        # Create the Besluit in the BRC
        besluit = client('brc').create('besluit', {
            # TODO: VerantwoordelijkeOrganisatie...
            'verantwoordelijkeOrganisatie': '245122461',
            'besluittype': form_data['besluittype_url'],
            'zaak': self.zaak['url'],
            'datum': isodate(),
            'toelichting': form_data['toelichting'],
            'bestuursorgaan': 'string',
            'ingangsdatum': isodate(),
            # 'vervaldatum': '2018-11-21',
            # 'vervalreden': 'tijdelijk',
            # 'vervalredenWeergave': 'string',
            # 'publicatiedatum': '2018-11-21',
            # 'verzenddatum': '2018-11-21',
            # 'uiterlijkeReactiedatum': '2018-11-21'
        })

        messages.add_message(self.request, messages.SUCCESS, 'Besluit succesvol toegevoegd.')

        return super().form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        # Retrieve available StatusTypes of this ZaakType in the ZTC
        # TODO: There is no "besluittype" element in ZaakType.
        # TODO: There is also no filter for besluittype_list on zaaktype.
        # besluittypes_by_url = api_response_list_to_dict(
        #     client('ztc').list('besluittype', catalogus_uuid=self.config.ztc_catalogus_uuid, query_params={'zaaktype': self.zaak['zaaktype']})
        # )
        # besluittype_choices = [(url, obj['omschrijving']) for url, obj in besluittypes_by_url.items()]

        # TODO: Workaround: The reverse relation exists: Each besluittype has 0
        # or more zaaktypes but we need to list ALL besluittypes.
        besluittype_list = self.ztc_client.list('besluittype', catalogus_uuid=self.catalogus_uuid)
        besluittype_choices = []
        for besluittype in besluittype_list:
            # TODO (in the workaround): Enable filtering, but this can only be
            # done once the ZTC Admin allows us to set this.
            # if self.zaak['zaaktype'] in besluittype['zaaktypes']:
                besluittype_choices.append(
                    (besluittype['url'], besluittype['omschrijving'])
                )
        # End workaround

        form_kwargs.update({
            'besluit_choices': besluittype_choices
        })

        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Retrieve a list of Besluiten
        besluit_list = client('brc').list('besluit', query_params={'zaak': self.zaak['url']})
        besluittypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('besluittype', catalogus_uuid=self.catalogus_uuid)
        )
        # Amend the resulting besluiten with their respective type.
        for besluit in besluit_list:
            besluit['besluittype_embedded'] = besluittypes_by_url.get(besluit['besluittype'], None)

        context.update({
            'zaak_uuid': self.zaak_uuid,
            'besluit_list': besluit_list,
        })
        return context
