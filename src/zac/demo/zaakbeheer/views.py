from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView, FormView

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

        zaken = zrc_client.list('zaak')
        # Workaround: The status should be done with embedding when requesting a list of Zaken.
        statussen = zrc_client.list('status')
        statussen_by_url = dict([
            (status['url'], status) for status in statussen
        ])
        # TODO: The by-url pattern might be so common it should be in the client.

        zaaktypen = ztc_client.list('zaaktype', catalogus_uuid=settings.DEMO_ZTC_CATALOGUS_UUID)
        zaaktypes_by_url = dict([
            (zaaktype['url'], zaaktype) for zaaktype in zaaktypen
        ])

        # Workaround: We cannot get a full list of all Statustypes, so we make a call for each Zaaktype, to get the
        # available Statustypes.
        statustypen = []
        for zaaktype in zaaktypen:
            # Workaround: UUID is not part of the serialiser yet, otherwise it was simply: zaaktype['uuid']
            zaaktype_uuid = get_uuid(zaaktype['url'])
            statustypen += ztc_client.list('statustype', catalogus_uuid=settings.DEMO_ZTC_CATALOGUS_UUID, zaaktype_uuid=zaaktype_uuid)
        statustypen_by_url = dict([
            (statustype['url'], statustype) for statustype in statustypen
        ])

        # Construct template vars.
        headers = ['#', 'Bronorganisatie', 'Type', 'Status', 'Statustype', 'Registratiedatum']
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
                status['statustoelichting'] if status else '(onbekend)',
                statustype['omschrijving'] if statustype else '(onbekend)',
                zaak['registratiedatum'],
            ])

        context.update({
            'header': headers,
            'rows': rows,
            'log_entries': Log.entries()
        }