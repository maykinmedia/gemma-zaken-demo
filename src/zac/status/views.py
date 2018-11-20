import requests

from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, ChoiceItem

from zac.demo.models import SiteConfiguration


class StatusChoices(DjangoChoices):
    working = ChoiceItem('working', _('API beschikbaar'))
    unavailable = ChoiceItem('unavailable', _('API niet beschikbaar'))
    unreachable = ChoiceItem('unreachable', _('Server niet bereikbaar'))


def get_status(url):
    try:
        response = requests.get(url, timeout=1)
    except Exception:
        return StatusChoices.unreachable

    if response.status_code == 200:
        return StatusChoices.working
    return StatusChoices.unavailable


class StatusView(TemplateView):
    title = 'API Status'
    subtitle = 'Overzicht en status van alle APIs'
    template_name = 'status/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        config = SiteConfiguration.get_solo()
        services = config.get_services()

        entries = []
        for service, url in services.items():
            status = get_status(url)

            entries.append({
                'status': status,
                'name': service,
                'message': StatusChoices.labels[status],
                'url': url,
            })

        context.update({
            'entries': entries
        })

        return context
