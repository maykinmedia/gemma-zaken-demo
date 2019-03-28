from django.views.generic import TemplateView
from django.urls import reverse
from django.utils.safestring import mark_safe

from ..mixins import ZACViewMixin
from .models import UserNotification
from ..models import SiteConfiguration, client
from ..utils import (
    api_response_list_to_dict, extract_pagination_info, get_uuid, isodate
)


class ZaakListView(ZACViewMixin, TemplateView):
    title = 'Mijn gemeente'
    subtitle = 'Uw zaken bij de gemeente'
    template_name = 'demo/mijngemeente/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # FAKE: Filter relevant notifications for user
        notifications = UserNotification.objects.all()

        # Querysets are lazy, so we cast to list to force the database request
        # here, to prevent all notifications from being marked as read before
        # we actually show them in the template.
        context.update({
            'unread_messages': [n.json() for n in notifications.filter(read=False)],
            'read_messages': [n.json() for n in notifications.filter(read=True)],
        })

        # We consider "shown" as "read" :)
        notifications.update(read=True)

        config = SiteConfiguration.get_solo()

        # Retrieve all Zaken
        query_params = None
        page = self.request.GET.get('page')
        if page:
            query_params = {'page': page}

        zaken_response = client('zrc').list('zaak', query_params=query_params)

        # Use only the latest 5 Zaken
        zaken_response['results'] = zaken_response['results'][:5]

        # Retrieve a list of all ZaakTypen from the "main" ZTC
        zaaktypen = client('ztc').list('zaaktype', catalogus_uuid=config.ztc_catalogus_uuid)
        zaaktypes_by_url = api_response_list_to_dict(zaaktypen)

        # Construct template vars.
        headers = [
            '#',
            'Type',
            'Registratiedatum'
        ]
        rows = []

        for index, zaak in enumerate(zaken_response['results']):
            zaaktype = zaaktypes_by_url.get(zaak['zaaktype'])

            # If the ZaakType is not in the "main" ZTC, retrieve it manually.
            if zaaktype is None:
                zaaktype = client('ztc', url=zaak['zaaktype']).retrieve('zaaktype', url=zaak['zaaktype'])

                # Skip over Zaak with unknown Zaaktype.
                if zaaktype is None:
                    continue

            detail_url = reverse('demo:zaakbeheer-detail', kwargs={'uuid': get_uuid(zaak['url'])})

            rows.append([
                mark_safe('<a href="{}">{}</a>'.format(detail_url, index + 1)),
                zaaktype['omschrijving'] if zaaktype else '(onbekend)',
                zaak['registratiedatum'],
            ])

        context.update({
            'header': headers,
            'rows': rows,
            'pagination': extract_pagination_info(zaken_response),
        })

        return context
