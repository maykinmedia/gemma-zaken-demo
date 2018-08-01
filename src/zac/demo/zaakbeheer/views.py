import datetime

from django import forms
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import FormView, TemplateView

from zac.demo.models import SiteConfiguration
from zdsclient import zrc_client, ztc_client
from zdsclient.client import Log


def get_uuid(url):
    return url.rsplit('/', 1)[1].strip('/')


class ZaakListView(TemplateView):
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
        # Workaround: The status should be done with embedding when requesting a list of Zaken.
        statussen = zrc_client.list('status')
        statussen_by_url = dict([
            (status['url'], status) for status in statussen
        ])
        # TODO: The by-url pattern might be so common it should be in the client.

        zaaktypen = ztc_client.list('zaaktype', catalogus_uuid=config.ztc_catalogus_uuid)
        zaaktypes_by_url = dict([
            (zaaktype['url'], zaaktype) for zaaktype in zaaktypen
        ])

        # Workaround: We cannot get a full list of all Statustypes, so we make a call for each Zaaktype, to get the
        # available Statustypes.
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



class ZaakDetailForm(forms.Form):
    zaak_url = forms.CharField(widget=forms.HiddenInput)
    zaaktype = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    zaakidentificatie = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    bronorganisatie = forms.CharField()
    registratiedatum = forms.DateField()
    statustype_url = forms.ChoiceField(label='Status')
    status_toelichting = forms.CharField()
    toelichting = forms.CharField(widget=forms.Textarea)
    longitude = forms.FloatField(widget=forms.HiddenInput)
    latitude = forms.FloatField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        status_choices = kwargs.pop('status_choices')

        super().__init__(*args, **kwargs)

        self.fields['statustype_url'].choices = status_choices


class ZaakDetailView(FormView):
    title = 'Zaakbeheer'
    subtitle = 'Details van een Zaak uit het ZRC'
    template_name = 'demo/zaakbeheer/zaak_detail.html'
    form_class = ZaakDetailForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        Log.clear()

    def dispatch(self, request, *args, **kwargs):
        # Haal Zaak op uit ZRC
        zaak = zrc_client.retrieve('zaak', uuid=self.kwargs.get('uuid'))
        self.zaak = zaak

        # TODO: We should be able to filter on zaak, to get all (historical) statusses for this Zaak.
        # For now, we just retrieve the current status of this Zaak.
        status = zrc_client.retrieve('status', uuid=get_uuid(self.zaak['status']))
        self.zaak_status = status

        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('demo:zaakbeheer-detail', kwargs={'uuid': self.kwargs.get('uuid')})

    def form_valid(self, form):

        form_data = form.cleaned_data

        # TODO: Zaak-update doesn't exist yet. So we only update the status.

        # Check if it's a different status.
        if self.zaak_status['statusType'] != form_data['statustype_url']:
            status = zrc_client.create('status', {
                'zaak': form_data['zaak_url'],
                'statusType': form_data['statustype_url'],
                'datumStatusGezet': datetime.datetime.now().isoformat(),
                'statustoelichting': form_data['status_toelichting'],
            })

        messages.add_message(self.request, messages.SUCCESS, 'Zaak succesvol bijgewerkt.')

        return super().form_valid(form)

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        config = SiteConfiguration.get_solo()

        # Haal Zaaktype op.
        zaaktype = None
        if self.zaak['zaaktype']:
            zaaktype = ztc_client.retrieve('zaaktype', catalogus_uuid=config.ztc_catalogus_uuid, uuid=get_uuid(self.zaak['zaaktype']))

        # Haal mogelijke statusTypen op van deze Zaak.
        statustype_urls = zaaktype['statustypen']
        statustype_choices = []
        for statustype_url in statustype_urls:
            statustype = ztc_client.retrieve('statustype', catalogus_uuid=config.ztc_catalogus_uuid, zaaktype_uuid=get_uuid(self.zaak['zaaktype']), uuid=get_uuid(statustype_url))
            statustype_choices.append(
                (statustype_url, statustype['omschrijving'])
            )

        form_kwargs.update({
            'status_choices': statustype_choices
        })

        if 'initial' in form_kwargs:
            extra_initial = self.zaak
            extra_initial.update({
                'zaak_url': self.zaak['url'],
                'statustype_url': self.zaak_status['statusType'],
                'zaaktype': zaaktype['omschrijving'] if zaaktype else '(onbekend)',
                'status_toelichting': self.zaak_status['statustoelichting'],
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
        context.update({
            'log_entries': Log.entries(),
        })
        return context
