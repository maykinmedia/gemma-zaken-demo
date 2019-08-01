import json

from django import forms
from django.views.generic import FormView

from zac.demo.mixins import ZACViewMixin
from zac.demo.models import SiteConfiguration, client
from zac.demo.utils import get_uuid, api_response_list_to_dict


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


class ZaakMapView(ZACViewMixin, FormView):
    title = 'Open data'
    subtitle = 'Toon alle openbare zaak data'
    template_name = 'demo/opendata/zaak_map.html'
    form_class = CoordinatesForm

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()

        config = SiteConfiguration.get_solo()

        zaaktypen_by_url = api_response_list_to_dict(
            client('ztc').list('zaaktype', query_params={
                'catalogus': config.ztc_catalogus_url
            })
        )
        zaaktype_choices = [(url, obj['omschrijving']) for url, obj in zaaktypen_by_url.items()]

        form_kwargs.update({
            'zaaktype_choices': zaaktype_choices
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
        zaken = client('zrc').operation('zaak__zoek', search_data)

        return self.render_to_response(
            self.get_context_data(
                form=form,
                # For simplicity, we just show the first page.
                zaken_json=json.dumps(zaken['results']),
            )
        )
