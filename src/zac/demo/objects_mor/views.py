import datetime
import logging

from django import forms
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, TemplateView

from ..api import (
    get_objects_grouped, get_objecttype_choices
)
from ..mixins import ZACViewMixin
from ..models import SiteConfiguration, client

logger = logging.getLogger(__name__)


class ObjectMorCreateForm(forms.Form):
    uw_naam = forms.CharField(required=False)
    uw_email_adres = forms.EmailField(label='Uw e-mail adres', required=False)

    toelichting = forms.CharField(widget=forms.Textarea)
    objecttype = forms.ChoiceField()
    object = forms.URLField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['objecttype'].choices = get_objecttype_choices()
        self.fields['object'].widget.attrs['placeholder'] = _("Put url or choose object on the map")


class ObjectMorCreateView(ZACViewMixin, FormView):
    title = 'Melding Openbare Ruimte'
    subtitle = 'Maak een nieuwe melding'

    template_name = 'demo/objects_mor/objects_mor_create.html'
    form_class = ObjectMorCreateForm
    success_url = reverse_lazy('demo:objects-mor-thanks')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # for demo purposes we'll retrieve objects with all objecttypes
        # TODO get objects of a specific objecttype in AJAX request
        object_groups = get_objects_grouped()
        context["object_groups"] = object_groups

        return context

    def form_valid(self, form):
        config = SiteConfiguration.get_solo()

        # Haal ZaakType:Melding Openbare Ruimte uit het ZTC
        zaaktype = client('ztc', request=self.request).retrieve(
            'zaaktype',
            catalogus_uuid=config.ztc_catalogus_uuid,
            uuid=config.ztc_mor_zaaktype_uuid,
        )
        # Haal StatusType:Nieuw uit het ZTC
        status_type = client('ztc', request=self.request).retrieve(
            'statustype',
            catalogus_uuid=config.ztc_catalogus_uuid,
            zaaktype_uuid=config.ztc_mor_zaaktype_uuid,
            uuid=config.ztc_mor_statustype_new_uuid,
        )

        # Verwerk de melding informatie...
        form_data = form.cleaned_data
        print("form_data=", form_data)

        return super().form_valid(form)


class ObjectMorThanksView(ZACViewMixin, TemplateView):
    title = 'Melding Openbare Ruimte'
    subtitle = 'Bedankt voor uw melding'

    template_name = 'demo/objects_mor/objects_mor_thanks.html'

    keep_logs = True
