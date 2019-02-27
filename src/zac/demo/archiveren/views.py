import copy
import datetime
import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView
from djchoices import DjangoChoices, ChoiceItem

from ..mixins import ZACViewMixin
from ..models import SiteConfiguration, client
from ..utils import isodate

logger = logging.getLogger(__name__)


def get_uuid(url, index=-1):
    return url.split('/')[index]


def prettify_enum_value(val):
    if val is None:
        return '(geen)'
    return val.replace('_', ' ').capitalize()


class ArchiverenListView(ZACViewMixin, TemplateView):
    title = 'Archivering'
    subtitle = 'Lijst van Zaken uit het ZRC t.b.v. archiveren'
    template_name = 'demo/archiveren/archiveren_list.html'

    def _pre_dispatch(self, request, *args, **kwargs):
        self.zrc_client = client('zrc')

    def post(self, request, *args, **kwargs):
        zaak_url_list = self.request.POST.getlist('zaak')

        # TODO: Implementation requires version 0.9.2 of the gemma-zds-client
        # but that messes up slashes...
        #
        # for zaak_url in zaak_url_list:
        #     self.zrc_client.delete('zaak', url=zaak_url)
        messages.add_message(self.request, messages.WARNING, 'DELETE ...\n\n{}'.format(
            '\n'.join(zaak_url_list)
        ))

        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def get_success_url(self, *args, **kwargs):
        return '{}?keep-logs=true'.format(
            reverse('demo:archiveren-index')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        filter = self.request.GET.get('filter', None)
        if filter == 'vernietigingslijst':
            query_params = {
                'archiefactiedatum__lt': isodate(datetime.date.today()),
                'archiefnominatie': 'vernietigen',
                'archiefstatus': 'nog_te_archiveren',
            }
        elif filter == 'overbrenglijst':
            query_params = {
                'archiefactiedatum__lt': isodate(datetime.date.today()),
                'archiefnominatie': 'blijvend_bewaren',
                'archiefstatus': 'nog_te_archiveren',
            }
        else:
            query_params = None

        zaken = client('zrc').list('zaak', query_params=query_params)

        rows = []
        for index, zaak in enumerate(zaken):
            detail_url = reverse('demo:archiveren-detail', kwargs={'uuid': get_uuid(zaak['url'])})

            if 'zac.demo.zaakbeheer' in settings.INSTALLED_APPS:
                zaak_detail_url = reverse('demo:zaakbeheer-detail', kwargs={'uuid': get_uuid(zaak['url'])})
            else:
                zaak_detail_url = '#'

            rows.append({
                'url': zaak['url'],
                'detail_url': detail_url,
                'zaak_detail_url': zaak_detail_url,
                'registratiedatum': zaak['registratiedatum'],
                'einddatum': zaak['einddatum'] if zaak['einddatum'] else '(geen)',
                'archiefactiedatum': zaak['archiefactiedatum'] if zaak['archiefactiedatum'] else '(geen)',
                'archiefnominatie': prettify_enum_value(zaak['archiefnominatie']),
                'archiefstatus': prettify_enum_value(zaak['archiefstatus']),
            })

        context.update({
            'filter': filter,
            'rows': rows,
        })

        return context


class Archiefnominatie(DjangoChoices):
    blijvend_bewaren = ChoiceItem('blijvend_bewaren', 'Blijvend bewaren')
    vernietigen = ChoiceItem('vernietigen', 'Vernietigen')


class Archiefstatus(DjangoChoices):
    nog_te_archiveren = ChoiceItem('nog_te_archiveren', 'Nog te archiveren')
    gearchiveerd = ChoiceItem('gearchiveerd', 'Gearchiveerd')
    gearchiveerd_procestermijn_onbekend = ChoiceItem('gearchiveerd_procestermijn_onbekend', 'Gearchiveerd (procestermijn onbekend)')
    overgedragen = ChoiceItem('overgedragen', 'Overgedragen')
    # After deliberation this element was removed because "vernietigd" means
    # it's really gone and the status wouldn't make sense:
    #
    # vernietigd = ChoiceItem('vernietigd', 'Vernietigd')


class ZaakArchiefForm(forms.Form):
    zaak_url = forms.CharField(widget=forms.HiddenInput)
    registratiedatum = forms.DateField(widget=forms.DateInput(attrs={'readonly': 'readonly'}), required=False)
    einddatum = forms.DateField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), required=False)
    archiefactiedatum = forms.DateField(required=False)
    archiefnominatie = forms.ChoiceField(choices=Archiefnominatie.choices, required=False)
    archiefstatus = forms.ChoiceField(choices=Archiefstatus.choices, required=False)


class ArchiverenDetailView(ZACViewMixin, FormView):
    title = 'Archiveren'
    subtitle = 'Details van een Zaak uit het ZRC t.b.v. archiveren'
    template_name = 'demo/archiveren/archiveren_detail.html'
    form_class = ZaakArchiefForm

    def _pre_dispatch(self, request, *args, **kwargs):
        self.config = SiteConfiguration.get_solo()

        # Haal Zaak op uit ZRC
        self.zrc_client = client('zrc')
        zaak = self.zrc_client.retrieve('zaak', uuid=self.kwargs.get('uuid'))
        self.zaak = zaak
        self.zaak_uuid = get_uuid(self.zaak['url'])

    def get_success_url(self):
        return '{}?keep-logs=true'.format(
            reverse('demo:archiveren-detail', kwargs={'uuid': self.kwargs.get('uuid')})
        )

    def form_valid(self, form):
        form_data = form.cleaned_data

        # Update the Zaak in the ZRC
        self.zrc_client.partial_update('zaak', uuid=self.zaak_uuid, data={
            'archiefactiedatum': isodate(form_data['archiefactiedatum']) if form_data['archiefactiedatum'] else None,
            'archiefnominatie': form_data['archiefnominatie'],
            'archiefstatus': form_data['archiefstatus'],
        })

        messages.add_message(self.request, messages.SUCCESS, 'Zaak succesvol bijgewerkt.')

        return super().form_valid(form)

    def get_initial(self):
        initial = super().get_initial()
        initial.update(copy.deepcopy(self.zaak))
        initial['zaak_url'] = self.zaak['url']
        return initial
