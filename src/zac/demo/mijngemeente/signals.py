import datetime
import json

from django.contrib.auth import user_logged_in
from django.dispatch import receiver
from django.urls import reverse

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


@receiver(user_logged_in)
def my_callback(sender, **kwargs):
    user = kwargs.get('user')

    # Typically, the logged in user in the Mijn Gemeente app, but for now we
    # just show for everyone.
    topic = 'notifications_everyone'


    data = {
        'title': f'{user.username} is ingelogd!',
        'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'body': None,
        'reference': user.pk,
        'url': reverse('admin:accounts_user_change', args=(user.pk, )),
    }

    # No daemon needed for this, since it's an event that happens in our own
    # application. Ofcourse, when we want to store notifications from the
    # Notification Component, we need a daemonish thingy.
    Notification.objects.create(
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
