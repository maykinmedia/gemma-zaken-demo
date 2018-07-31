import json

from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import FormView, TemplateView

from zac.demo.models import SiteConfiguration
from zdsclient import zrc_client, ztc_client
from zdsclient.client import Log


def get_uuid(url):
    return url.rsplit('/', 1)[1].strip('/')


class CoordinatesForm(forms.Form):
    latitude = forms.FloatField(widget=forms.HiddenInput)
    longitude = forms.FloatField(widget=forms.HiddenInput)
    radius = forms.IntegerField(widget=forms.HiddenInput)

    coordinates = forms.CharField(widget=forms.HiddenInput)
    zaak_type = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        zaaktype_choices = kwargs.pop('zaaktype_choices')

        super().__init__(*args, **kwargs)

        self.fields['zaak_type'].choices = zaaktype_choices


class ZaakMapView(FormView):
    title = 'Open data'
    subtitle = 'Toon alle openbare zaak data'
    template_name = 'demo/opendata/zaak_map.html'
    form_class = CoordinatesForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        Log.clear()

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        config = SiteConfiguration.get_solo()

        zaak_typen = ztc_client.list('zaaktype', catalogus_uuid=config.ztc_catalogus_uuid)
        form_kwargs.update({
            'zaaktype_choices': [(zaak_type['url'], zaak_type['omschrijving']) for zaak_type in zaak_typen]
        })

        return form_kwargs

    def form_valid(self, form):
        form_data = form.cleaned_data

        search_data = {
            'zaakgeometrie': {
                'within': {
                    'type': 'Polygon',
                    'coordinates': [
                        json.loads(form_data['coordinates'])
                    ]
                }
            }
        }

        # TODO: Filter on public status and type
        zaken = zrc_client.operation('zaak__zoek', search_data)

        return self.render_to_response(
            self.get_context_data(
                form=form,
                zaken_json=json.dumps(zaken),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'log_entries': Log.entries()
        })

        return context
