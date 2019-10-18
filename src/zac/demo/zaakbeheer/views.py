import copy
import datetime
import logging

from django import forms
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import FormView, TemplateView

import requests
from dictdiffer import diff
from djchoices import ChoiceItem, DjangoChoices
from zds_client.client import ClientError

from ..mixins import ZACViewMixin
from ..models import SiteConfiguration, client
from ..utils import (
    api_response_list_to_dict, extract_pagination_info, fetch_paginated_list,
    format_dict_diff, get_uuid, isodate
)

logger = logging.getLogger(__name__)


class ZaakListView(ZACViewMixin, TemplateView):
    title = 'Zaakafhandelcomponent (ZAC)'
    subtitle = 'Lijst van Zaken uit het ZRC'
    template_name = 'demo/zaakbeheer/zaak_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        config = SiteConfiguration.get_solo()

        # Retrieve all Zaken
        query_params = None
        page = self.request.GET.get('page')
        if page:
            query_params = {'page': page}

        zaken_response = client('zrc').list('zaak', query_params=query_params)

        # TODO: Workaround: The status should be done with embedding when
        # requesting a list of Zaken.
        statusses_by_url = api_response_list_to_dict(fetch_paginated_list(client('zrc'), 'status'))

        # Retrieve a list of all ZaakTypen from the "main" ZTC
        zaaktypen = client('ztc').list('zaaktype', catalogus_uuid=config.ztc_catalogus_uuid)['results']
        zaaktypes_by_url = api_response_list_to_dict(zaaktypen)

        # Retrieve a list of StatusTypen from the "main" ZTC.
        # TODO: Workaround: We cannot get a full list of all StatusTypes, so we
        # make a call for each Zaaktype, to get the available Statustypes.
        statustypen = []
        for zaaktype in zaaktypen:
            # Workaround: UUID is not part of the serialiser yet, otherwise it was simply: zaaktype['uuid']
            statustypen += (
                client('ztc')
                .list(
                    'statustype',
                    catalogus_uuid=config.ztc_catalogus_uuid,
                    zaaktype_uuid=get_uuid(zaaktype['url'])
                )['results']
            )
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

        zaaktypes = {}
        rows = []

        for index, zaak in enumerate(zaken_response['results']):
            zaaktype = zaaktypes_by_url.get(zaak['zaaktype'])

            # If the ZaakType is not in the "main" ZTC, retrieve it manually.
            if zaaktype is None:
                try:
                    zaaktype = zaaktypes[zaak['zaaktype']]
                except:
                    zaaktype = client('ztc', url=zaak['zaaktype']).retrieve('zaaktype', url=zaak['zaaktype'])

                # Skip over Zaak with unknown Zaaktype.
                if zaaktype is None:
                    continue
                zaaktypes[zaak['zaaktype']] = zaaktype

            status = statusses_by_url.get(zaak['status'])
            statustype = None
            if status:
                statustype = statustypen_by_url.get(status['statustype'])

                # If the StatusType is not in the "main" ZTC, retrieve it
                # manually.
                if statustype is None:
                    statustype = (
                        client('ztc', url=status['statustype'])
                        .retrieve('statustype', url=status['statustype'])
                    )

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
            'pagination': extract_pagination_info(zaken_response),
        })

        return context


class ZaakForm(forms.Form):
    zaak_url = forms.CharField(widget=forms.HiddenInput)
    zaaktype = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    identificatie = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    bronorganisatie = forms.CharField()
    registratiedatum = forms.DateField()
    einddatum = forms.DateField(widget=forms.DateInput(attrs={'readonly': 'readonly'}), required=False)
    toelichting = forms.CharField(widget=forms.Textarea, required=False)
    longitude = forms.FloatField(widget=forms.HiddenInput, required=False)
    latitude = forms.FloatField(widget=forms.HiddenInput, required=False)


class ZaakDetailView(ZACViewMixin, FormView):
    title = 'Zaakafhandelcomponent (ZAC)'
    subtitle = 'Details van een Zaak uit het ZRC'
    template_name = 'demo/zaakbeheer/zaak_detail.html'
    form_class = ZaakForm

    def _pre_dispatch(self, request, *args, **kwargs):
        self.config = SiteConfiguration.get_solo()

        # Haal Zaak op uit ZRC
        self.zrc_client = client('zrc')
        zaak = self.zrc_client.retrieve('zaak', uuid=self.kwargs.get('uuid'))
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
        self.zrc_client.partial_update('zaak', uuid=self.zaak_uuid, data={
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
        # TODO: grab other pages
        status_list = self.zrc_client.list('status', query_params={'zaak': self.zaak['url']})["results"]
        statustypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('statustype', catalogus_uuid=self.catalogus_uuid, zaaktype_uuid=get_uuid(self.zaak['zaaktype']))
        )
        # Amend the resulting besluiten with their respective type.
        for status in status_list:
            status['statustype_embedded'] = statustypes_by_url.get(status['statustype'], None)

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
        besluit_list = client('brc').list('besluit', query_params={'zaak': self.zaak['url']})['results']
        besluittypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('besluittype', catalogus_uuid=self.catalogus_uuid)
        )
        # Amend the resulting besluiten with their respective type.
        for besluit in besluit_list:
            besluit['besluittype_embedded'] = besluittypes_by_url.get(besluit['besluittype'], None)

        # Retrieve the Resultaat and ResultaatType
        resultaat = None
        resultaat_type = None

        if self.zaak['resultaat']:
            resultaat = self.zrc_client.retrieve('resultaat', url=self.zaak['resultaat'])
            try:
                resultaat_type = self.ztc_client.retrieve('resultaattype', url=resultaat['resultaattype'])
            except ClientError as e:
                logger.exception(e)
            resultaat['resultaattype_embedded'] = resultaat_type

        # Retrieve list of AuditTrails associated with this Zaak
        zrc_audittrail_list = client('zrc').list('audittrail', zaak_uuid=get_uuid(self.zaak['url']))

        drc_audittrail_list = []
        for oio in document_relation_list:
            drc_audittrail_list += client('drc').list(
                'audittrail',
                enkelvoudiginformatieobject_uuid=get_uuid(oio['informatieobject'])
            )

        brc_audittrail_list = []
        for besluit in besluit_list:
            brc_audittrail_list += client('brc').list('audittrail', besluit_uuid=get_uuid(besluit['url']))

        audittrail_list = zrc_audittrail_list + drc_audittrail_list + brc_audittrail_list

        for audit in audittrail_list:
            oud = audit['wijzigingen']['oud'] or {}
            nieuw = audit['wijzigingen']['nieuw'] or {}

            changes = list(diff(oud, nieuw))
            audit['wijzigingen'] = format_dict_diff(changes)
            audit['aanmaakdatum'] = datetime.datetime.strptime(audit['aanmaakdatum'], "%Y-%m-%dT%H:%M:%S.%fZ")

        # Betrokkenen/Rollen
        # TODO: fetch extra pages
        rollen_list = self.zrc_client.list('rol', query_params={
            'zaak': self.zaak['url'],
        })['results']

        for rol in rollen_list:
            if rol['betrokkene']:
                personen = get_personen(self.config, self.zrc_client, url=rol['betrokkene'])
                if personen:
                    rol['betrokkeneNaam'] = personen[0][1]['naam']['aanschrijfwijze']

        context.update({
            'zaak_uuid': self.zaak_uuid,
            'status_list': status_list,
            'document_list': document_list,
            'besluit_list': besluit_list,
            'rollen_list': rollen_list,
            'resultaat': resultaat,
            'audittrail_list': sorted(audittrail_list, key=lambda x: x['aanmaakdatum'])
        })
        return context


class StatusForm(forms.Form):
    statustype_url = forms.ChoiceField(label='Status', required=True)
    toelichting = forms.CharField()

    def __init__(self, *args, **kwargs):
        status_choices = kwargs.pop('status_choices')

        super().__init__(*args, **kwargs)

        self.fields['statustype_url'].choices = status_choices


class StatusCreateView(ZACViewMixin, FormView):
    title = 'ZAC - Statussen'
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
            'statustype': form_data['statustype_url'],
            'datumStatusGezet': datetime.datetime.now().isoformat(),
            'statustoelichting': form_data['toelichting'],
        })

        messages.add_message(self.request, messages.SUCCESS, 'Status succesvol toegevoegd.')

        return super().form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        # Retrieve available StatusTypes of this ZaakType in the ZTC
        statustypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('statustype', query_params={
                'zaaktype': self.zaak['zaaktype'],
            })
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
        # TODO: fetch extra pages
        status_list = client('zrc').list('status', query_params={'zaak': self.zaak['url']})['results']
        statustypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('statustype', catalogus_uuid=self.catalogus_uuid, zaaktype_uuid=get_uuid(self.zaak['zaaktype']))
        )
        # Amend the resulting besluiten with their respective type.
        for status in status_list:
            status['statustype_embedded'] = statustypes_by_url.get(status['statustype'], None)

        context.update({
            'zaak_uuid': self.zaak_uuid,
            'status_list': status_list,
        })
        return context


class BesluitForm(forms.Form):
    besluittype_url = forms.ChoiceField(label='Besluit', required=True)
    toelichting = forms.CharField()

    def __init__(self, *args, **kwargs):
        besluit_choices = kwargs.pop('besluit_choices')

        super().__init__(*args, **kwargs)

        self.fields['besluittype_url'].choices = besluit_choices


class BesluitCreateView(ZACViewMixin, FormView):
    title = 'ZAC - Besluiten'
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

        zaaktype = self.ztc_client.retrieve('zaaktype', url=self.zaak['zaaktype'])
        besluittype_list = self.ztc_client.list('besluittype', query_params={
                'catalogus': zaaktype['catalogus'],
            })

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


class ResultaatForm(forms.Form):
    resultaattype_url = forms.ChoiceField(label='Resultaat', required=True)
    toelichting = forms.CharField()

    def __init__(self, *args, **kwargs):
        resultaat_choices = kwargs.pop('resultaat_choices')

        super().__init__(*args, **kwargs)

        self.fields['resultaattype_url'].choices = resultaat_choices


class ResultaatEditView(ZACViewMixin, FormView):
    title = 'ZAC - Resultaat'
    subtitle = 'Resultaat beheren van deze zaak'
    template_name = 'demo/zaakbeheer/resultaat_edit.html'
    form_class = ResultaatForm

    def _pre_dispatch(self, request, *args, **kwargs):
        self.config = SiteConfiguration.get_solo()

        # Retrieve Zaak from ZRC
        self.zrc_client = client('zrc')
        self.zaak = self.zrc_client.retrieve('zaak', uuid=self.kwargs.get('uuid'))
        self.zaak_uuid = get_uuid(self.zaak['url'])

        # Work with any configured ZTC.
        self.ztc_client = client('ztc', url=self.zaak['zaaktype'])
        # TODO: Make a nicer way to get the catalogus UUID.
        self.catalogus_uuid = get_uuid(self.zaak['zaaktype'], -3)

    def get_success_url(self):
        return '{}?keep-logs=true'.format(
            reverse('demo:zaakbeheer-resultaatedit', kwargs={'uuid': self.kwargs.get('uuid')})
        )

    def form_valid(self, form):
        form_data = form.cleaned_data

        # Create the Resultaat in the ZRC
        data = {
            'resultaattype': form_data['resultaattype_url'],
            'zaak': self.zaak['url'],
            'toelichting': form_data['toelichting'],
        }

        if not self.zaak['resultaat']:
            self.zrc_client.create('resultaat', data)
            messages.add_message(self.request, messages.SUCCESS, 'Resultaat succesvol toegevoegd.')
        else:
            self.zrc_client.update('resultaat', data, url=self.zaak['resultaat'])
            messages.add_message(self.request, messages.SUCCESS, 'Resultaat succesvol gewijzigd.')

        return super().form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        resultaattype_list = self.ztc_client.list(
            'resultaattype',
            catalogus_uuid=self.catalogus_uuid,
            query_params={'zaaktype': self.zaak['zaaktype']}
        )
        resultaattype_choices = []
        for resultaattype in resultaattype_list:
            resultaattype_choices.append(
                (resultaattype['url'], resultaattype['omschrijving'])
            )

        form_kwargs.update({
            'resultaat_choices': resultaattype_choices
        })

        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        resultaat = None
        resultaat_type = None

        if self.zaak['resultaat']:
            resultaat = self.zrc_client.retrieve('resultaat', url=self.zaak['resultaat'])
            resultaat_type = self.ztc_client.retrieve('resultaattype', url=resultaat['resultaattype'])

        context.update({
            'zaak_uuid': self.zaak_uuid,
            'resultaat_type': resultaat_type,
            'resultaat': resultaat,
        })
        return context


class Rol(DjangoChoices):
    # TODO: We can probably load these from the OAS...
    adviseur = ChoiceItem('Adviseur', 'Adviseur')
    behandelaar = ChoiceItem('Behandelaar', 'Behandelaar')
    belanghebbende = ChoiceItem('Belanghebbende', 'Belanghebbende')
    beslisser = ChoiceItem('Beslisser', 'Beslisser')
    initiator = ChoiceItem('Initiator', 'Initiator')
    klantcontacter = ChoiceItem('Klantcontacter', 'Klantcontacter')
    zaakcoordinator = ChoiceItem('Zaakcoördinator', 'Zaakcoördinator')
    mede_initiator = ChoiceItem('Mede-initiator', 'Mede-initiator')


class BetrokkeneForm(forms.Form):
    betrokkene_url = forms.ChoiceField(label='Persoon', required=True)
    roltype_url = forms.ChoiceField(label='Rol', required=True)
    rol_toelichting = forms.CharField(label='Toelichting', required=False)

    def __init__(self, *args, **kwargs):
        betrokkene_choices = kwargs.pop('betrokkene_choices')
        roltype_choices = kwargs.pop('roltype_choices')

        super().__init__(*args, **kwargs)

        self.fields['betrokkene_url'].choices = betrokkene_choices
        self.fields['roltype_url'].choices = roltype_choices


def get_personen(config, client, bsn=None, url=None):
    """
    Grabs personen from the BRP. Didn't test any error-scenario's.

    Very, very basic but works for API-lab.

    :param config:
    :param client:
    :param bsn:
    :param url:
    :return:
    """
    personen = []

    if bsn:
        url = config.brp_base_url + f'ingeschrevenpersonen/{bsn}'
    try:
        response = requests.get(url, headers={'X-API-KEY': config.brp_api_key})
    except Exception:
        return personen

    # Add log entry
    client._log.add(
        'brp',
        url,
        'GET',
        {},
        {},
        response.status_code,
        dict(response.headers),
        response.content,
    )

    # Make the URL's part of the data.
    if response.status_code == 200:
        data = response.json()
        personen.append(
            (
                url,
                data,
            )
        )

    return personen


class BetrokkeneCreateView(ZACViewMixin, FormView):
    title = 'ZAC - Betrokkene'
    subtitle = 'Betrokkenen beheren van deze zaak'
    template_name = 'demo/zaakbeheer/betrokkene_create.html'
    form_class = BetrokkeneForm

    def _pre_dispatch(self, request, *args, **kwargs):
        self.config = SiteConfiguration.get_solo()

        # Retrieve Zaak from ZRC
        self.zrc_client = client('zrc')
        self.zaak = self.zrc_client.retrieve('zaak', uuid=self.kwargs.get('uuid'))
        self.zaak_uuid = get_uuid(self.zaak['url'])

        # # Work with any configured ZTC.
        self.ztc_client = client('ztc', url=self.zaak['zaaktype'])

    def post(self, request, *args, **kwargs):
        if request.POST.get('bsn'):
            # Update form with hits.
            return self.render_to_response(self.get_context_data(form=self.get_form()))
        else:
            return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return '{}?keep-logs=true'.format(
            reverse('demo:zaakbeheer-betrokkenecreate', kwargs={'uuid': self.kwargs.get('uuid')})
        )

    def form_valid(self, form):
        form_data = form.cleaned_data

        # Create the Rol in the ZRC
        data = {
            'zaak': self.zaak['url'],
            'betrokkene': form_data['betrokkene_url'],
            'betrokkeneType': 'natuurlijk_persoon',
            'roltype': form_data['roltype_url'],
            'roltoelichting': form_data['rol_toelichting'],
        }

        self.zrc_client.create('rol', data)
        messages.add_message(self.request, messages.SUCCESS, 'Betrokkene succesvol toegevoegd.')

        return super().form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        personen_choices = [
            ('', '(leeg)')
        ]

        # Search persons on BSN if search was performed.
        # TODO: Handle search better but keep transaction log as is for demo
        # purposes.
        bsn = self.request.GET.get('bsn', None)
        if bsn:
            personen = get_personen(self.config, self.zrc_client, bsn)

            for url, persoon_data in personen:
                personen_choices.append(
                    (
                        url,
                        persoon_data['naam']['aanschrijfwijze'],
                    )
                )

        # Retrieve available StatusTypes of this ZaakType in the ZTC
        roltypes_by_url = api_response_list_to_dict(
            self.ztc_client.list('roltype', query_params={
                'zaaktype': self.zaak['zaaktype'],
            })
        )
        roltype_choices = [
            (
                url,
                obj['omschrijving'] if obj['omschrijving'] else obj['omschrijvingGeneriek']
            ) for url, obj in roltypes_by_url.items()
        ]

        form_kwargs.update({
            'betrokkene_choices': personen_choices,
            'roltype_choices': roltype_choices
        })

        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: fetch extra pages
        rollen_list = self.zrc_client.list('rol', query_params={
            'zaak': self.zaak['url'],
        })['results']

        for rol in rollen_list:
            if rol['betrokkene']:
                # Naive approach, but works for API-lab
                personen = get_personen(self.config, self.zrc_client, url=rol['betrokkene'])
                if personen:
                    rol['betrokkeneNaam'] = personen[0][1]['naam']['aanschrijfwijze']

        context.update({
            'zaak_uuid': self.zaak_uuid,
            'rollen_list': rollen_list,
        })
        return context
