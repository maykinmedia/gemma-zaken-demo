from django.views.generic import TemplateView

from ..mixins import ZACViewMixin
from .models import UserNotification


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

        return context
