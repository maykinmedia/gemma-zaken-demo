import json
from django import forms
from django.views.generic import FormView

from zac.demo.mixins import ZACViewMixin
from zac.demo.models import SiteConfiguration
from zac.demo.utils import api_response_list_to_dict
from ..models import SiteConfiguration


def get_objecttype_choices():
    config = SiteConfiguration.get_solo()
    objecttypes_client = config.objecttypes_api.build_client()

    objecttypes_by_url = api_response_list_to_dict(
        objecttypes_client.list('objecttype')
    )
    objecttype_choices = [(url, obj['name']) for url, obj in objecttypes_by_url.items()]
    return objecttype_choices


class ObjectMapForm(forms.Form):
    # circle params are used to save circle after refreshing the page
    latitude = forms.FloatField(widget=forms.HiddenInput)
    longitude = forms.FloatField(widget=forms.HiddenInput)
    radius = forms.IntegerField(widget=forms.HiddenInput)

    coordinates = forms.CharField(widget=forms.HiddenInput)
    objecttype = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['objecttype'].choices = get_objecttype_choices()


class ObjectMapView(ZACViewMixin, FormView):
    title = 'Open data'
    subtitle = 'Toon alle openbare object data'
    template_name = 'demo/objectdata/object_map.html'
    form_class = ObjectMapForm

    def form_valid(self, form):
        config = SiteConfiguration.get_solo()
        objects_client = config.objects_api.build_client()

        form_data = form.cleaned_data

        search_data = {
            'geometry': {
                'within': {
                    'type': 'Polygon',
                    'coordinates': [
                        json.loads(form_data['coordinates'])
                    ]
                }
            },
            "type": form_data["objecttype"]
        }

        objects_data = objects_client.operation('object_search', search_data)

        return self.render_to_response(
            self.get_context_data(
                form=form,
                objects_json=objects_data,
            )
        )
