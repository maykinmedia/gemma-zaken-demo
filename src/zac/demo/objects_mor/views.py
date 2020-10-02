import datetime
import logging

from django import forms
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, TemplateView

from ..api import (
    create_object, get_objects_grouped, get_objecttype_choices,
    get_objecttype_melding
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

        all_choices = get_objecttype_choices()
        mor_objecttype = get_objecttype_melding()
        # can't make a complaint about complaint
        self.fields['objecttype'].choices = [
            choice for choice in all_choices if choice[0] != mor_objecttype["url"]
        ]
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
        context["object_groups"] = get_objects_grouped()

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

        # Maak een Zaak aan in het ZRC.
        # FIXME do I need to add zaak geometry?
        data = {
            'zaaktype': zaaktype['url'],
            'toelichting': form_data['toelichting'],
            'bronorganisatie': config.zrc_bronorganisatie,
            'registratiedatum': datetime.date.today().isoformat(),
            'startdatum': datetime.date.today().isoformat(),
            'verantwoordelijkeOrganisatie': config.zrc_bronorganisatie,
        }

        zaak = client('zrc', request=self.request).create('zaak', data)

        # Geef de Zaak een status in het ZRC.
        status = client('zrc', request=self.request).create('status', {
            'zaak': zaak['url'],
            'statustype': status_type['url'],
            'datumStatusGezet': datetime.datetime.now().isoformat(),
            'statustoelichting': 'Melding ontvangen',
        })

        # assign object the report is about to zaak
        objecttype_name = dict(get_objecttype_choices())[form_data['objecttype']]
        zaak_object_reason = client('zrc').create('zaakobject', {
            'zaak': zaak['url'],
            'object': form_data['object'],
            'objectType': "overige",
            'objectTypeOverige': objecttype_name
        })

        # retrieve melding object type
        objecttype_melding = get_objecttype_melding()
        # create melding object
        # FIXME do I need to add melding geometry?
        object_melding = create_object(
            {
                "type": objecttype_melding["url"],
                "record": {
                    "typeVersion": config.objecttypes_mor_objecttype_version,
                    "data": {
                        "description": form_data['toelichting']
                    },
                    "startDate": datetime.date.today().isoformat(),
                }
            }
        )

        #  assign melding object to zaak
        zaak_object_melding = client('zrc').create('zaakobject', {
            'zaak': zaak['url'],
            'object': object_melding["url"],
            'objectType': "overige",
            'objectTypeOverige': "melding"
        })

        return super().form_valid(form)


class ObjectMorThanksView(ZACViewMixin, TemplateView):
    title = 'Melding Openbare Ruimte'
    subtitle = 'Bedankt voor uw melding'

    template_name = 'demo/objects_mor/objects_mor_thanks.html'

    keep_logs = True
