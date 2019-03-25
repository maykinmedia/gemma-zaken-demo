import datetime
import json

from django.db import models
from django.utils import timezone

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils.safestring import mark_safe


class UserNotification(models.Model):
    # user = models...
    topic = models.CharField(max_length=200)
    message = models.TextField(blank=True)

    read = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ('-created', )

    def json(self):
        return json.loads(self.message)

    @classmethod
    def create_and_notify(cls, title, body, reference, url, topic=None):
        """
        Create a notification instance and relay via websocket.

        :param title:
        :param body:
        :param reference:
        :param url:
        :param topic:
        :return:
        """

        # Typically, the logged in user in the Mijn Gemeente app, but for now we
        # just show for everyone.
        if topic is None:
            topic = 'notifications_everyone'

        data = {
            'title': mark_safe(title),
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'body': mark_safe(body),
            'reference': reference,
            'url': url,
        }

        # No daemon needed for this, since it's an event that happens in our own
        # application. Ofcourse, when we want to store notifications from the
        # Notification Component, we need a daemonish thingy.
        cls.objects.create(
            topic=topic,
            message=json.dumps(data)
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            topic,
            {
                'type': 'notification_message',
                'message': data
            }
        )
