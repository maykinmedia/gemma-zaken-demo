import copy
import datetime
import logging

from django import forms
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import FormView, TemplateView

from zds_client.client import Log, ClientError

from ..clients import zrc_client, ztc_client, drc_client
from ..mixins import ExceptionViewMixin
from ..models import SiteConfiguration

logger = logging.getLogger(__name__)


def get_uuid(url):
    return url.rsplit('/', 1)[1].strip('/')


class ZaakListView(ExceptionViewMixin, TemplateView):
    title = 'Zaakbeheer'
    subtitle = 'Lijst van Zaken uit het ZRC'
    template_name = 'demo/zaakbeheer/zaak_list.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        Log.clear()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        config = SiteConfiguration.get_solo()

        zaken = zrc_client.list('zaak')
        # TODO: Workaround: The status should be done with embedding when
        # requesting a list of Zaken.
        statussen = zrc_client.list('status')
        statussen_by_url = dict([
            (status['url'], status) for status in statussen
        ])
        # TODO: The by-url pattern might be so common it should be in the client.

        zaaktypen = ztc_client.list('zaaktype', catalogus_uuid=config.ztc_catalogus_uuid)
        zaaktypes_by_url = dict([
            (zaaktype['url'], zaaktype) for zaaktype in zaaktypen
        ])

        # TODO: Workaround: We cannot get a full list of all Statustypes, so we
        # make a call for each Zaaktype, to get the available Statustypes.
        statustypen = []
        for zaaktype in zaaktypen:
            # Workaround: UUID is not part of the serialiser yet, otherwise it was simply: zaaktype['uuid']
            zaaktype_uuid = get_uuid(zaaktype['url'])
            statustypen += ztc_client.list('statustype', catalogus_uuid=config.ztc_catalogus_uuid, zaaktype_uuid=zaaktype_uuid)
        statustypen_by_url = dict([
            (statustype['url'], statustype) for statustype in statustypen
        ])

        # Construct template vars.
        headers = ['#', 'Bronorganisatie', 'Type', 'Status (type)', 'Status toelichting', 'Registratiedatum']
        rows = []
        for index, zaak in enumerate(zaken):
            zaaktype = zaaktypes_by_url.get(zaak['zaaktype'])
            status = statussen_by_url.get(zaak['status'])
            statustype = None
            if status:
                statustype = statustypen_by_url.get(status['statusType'])

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
            'log_entries': Log.entries()
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


class ZaakDetailView(ExceptionViewMixin, FormView):
    title = 'Zaakbeheer'
    subtitle = 'Details van een Zaak uit het ZRC'
    template_name = 'demo/zaakbeheer/zaak_detail.html'
    form_class = ZaakForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        Log.clear()

    def _pre_dispatch(self, request, *args, **kwargs):
        self.config = SiteConfiguration.get_solo()

        # Haal Zaak op uit ZRC
        zaak = zrc_client.retrieve('zaak', uuid=self.kwargs.get('uuid'))
        self.zaak = zaak
        self.zaak_uuid = get_uuid(self.zaak['url'])

    def get_success_url(self):
        return reverse('demo:zaakbeheer-detail', kwargs={'uuid': self.kwargs.get('uuid')})

    def form_valid(self, form):
        form_data = form.cleaned_data

        zrc_client.partial_update('zaak', uuid=self.zaak_uuid, data={
            'toelichting': form_data['toelichting']
        })

        messages.add_message(self.request, messages.SUCCESS, 'Zaak succesvol bijgewerkt.')

        return super().form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        # Haal Zaaktype op.
        zaaktype = None
        if self.zaak['zaaktype']:
            zaaktype = ztc_client.retrieve('zaaktype', catalogus_uuid=self.config.ztc_catalogus_uuid, uuid=get_uuid(self.zaak['zaaktype']))

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

        # Retrieve a status list
        status_list = zrc_client.list('status', query_params={'zaak': self.zaak['url']})
        # TODO: Replace with retrieving a list of all statustypes, once no longer nested
        for sl in status_list:
            statustype = ztc_client.retrieve('statustype', catalogus_uuid=self.config.ztc_catalogus_uuid, zaaktype_uuid=get_uuid(self.zaak['zaaktype']), uuid=get_uuid(sl['statusType']))
            sl['statusType_embedded'] = statustype

        # Retrieve a list of documents
        #
        # Look at the relation from the DRC-perspective to include documents
        # linked to Besluiten as well.
        document_relation_list = drc_client.list('objectinformatieobject', query_params={'object': self.zaak['url']})
        document_list = []
        for dr in document_relation_list:
            try:
                document = drc_client.retrieve('enkelvoudiginformatieobject', uuid=get_uuid(dr['informatieobject']))
            except ClientError as e:
                logger.exception(e)
                continue
            document_list.append(document)

        context.update({
            'zaak_uuid': self.zaak_uuid,
            'status_list': status_list,
            'document_list': document_list,
            'log_entries': Log.entries(),
        })
        return context


class ZaakStatusForm(forms.Form):
    statustype_url = forms.ChoiceField(label='Status')
    toelichting = forms.CharField()

    def __init__(self, *args, **kwargs):
        status_choices = kwargs.pop('status_choices')

        super().__init__(*args, **kwargs)

        self.fields['statustype_url'].choices = status_choices


class ZaakStatusCreateView(ExceptionViewMixin, FormView):
    title = 'Zaakbeheer - Statussen'
    subtitle = 'Status beheren van deze zaak'
    template_name = 'demo/zaakbeheer/zaakstatus_create.html'
    form_class = ZaakStatusForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        Log.clear()

    def _pre_dispatch(self, request, *args, **kwargs):
        self.config = SiteConfiguration.get_solo()

        # Haal Zaak op uit ZRC
        zaak = zrc_client.retrieve('zaak', uuid=self.kwargs.get('uuid'))
        self.zaak = zaak
        self.zaak_uuid = get_uuid(self.zaak['url'])

    def get_success_url(self):
        return reverse('demo:zaakbeheer-statuscreate', kwargs={'uuid': self.kwargs.get('uuid')})

    def form_valid(self, form):
        form_data = form.cleaned_data

        status = zrc_client.create('status', {
            'zaak': self.zaak['url'],
            'statusType': form_data['statustype_url'],
            'datumStatusGezet': datetime.datetime.now().isoformat(),
            'statustoelichting': form_data['toelichting'],
        })

        messages.add_message(self.request, messages.SUCCESS, 'Status succesvol toegevoegd.')

        return super().form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        # Haal Zaaktype op.
        zaaktype = None
        if self.zaak['zaaktype']:
            zaaktype = ztc_client.retrieve('zaaktype', catalogus_uuid=self.config.ztc_catalogus_uuid, uuid=get_uuid(self.zaak['zaaktype']))

        # Haal mogelijke statusTypen op van deze Zaak.
        statustype_urls = zaaktype['statustypen']
        statustype_choices = []
        for statustype_url in statustype_urls:
            statustype = ztc_client.retrieve('statustype', catalogus_uuid=self.config.ztc_catalogus_uuid, zaaktype_uuid=get_uuid(self.zaak['zaaktype']), uuid=get_uuid(statustype_url))
            statustype_choices.append(
                (statustype_url, statustype['omschrijving'])
            )

        form_kwargs.update({
            'status_choices': statustype_choices
        })

        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Retrieve a status list
        status_list = zrc_client.list('status', query_params={'zaak': self.zaak['url']})
        # TODO: Replace with retrieving a list of all statustypes, once no longer nested
        # TODO: Partially duplicated requests with those in get_form_kwargs
        for sl in status_list:
            statustype = ztc_client.retrieve('statustype', catalogus_uuid=self.config.ztc_catalogus_uuid, zaaktype_uuid=get_uuid(self.zaak['zaaktype']), uuid=get_uuid(sl['statusType']))
            sl['statusType_embedded'] = statustype

        context.update({
            'zaak_uuid': self.zaak_uuid,
            'status_list': status_list,
            'log_entries': Log.entries(),
        })
        return context
