from django import forms
from django.views.generic import FormView

from zac.demo.mixins import ZACViewMixin
from zac.demo.models import SiteConfiguration
from zac.demo.utils import api_response_list_to_dict


def get_objecttype_choices():
    config = SiteConfiguration.get_solo()
    objecttypes_client = config.objecttypes_api.build_client()

    objecttypes_by_url = api_response_list_to_dict(
        objecttypes_client.list('objecttype')
    )
    objecttype_choices = [(url, obj['name']) for url, obj in objecttypes_by_url.items()]
    return objecttype_choices


class ObjectMapForm(forms.Form):
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
