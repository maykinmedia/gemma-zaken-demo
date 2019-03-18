from django.contrib.auth import user_logged_in
from django.dispatch import receiver
from django.urls import reverse

from .models import UserNotification


@receiver(user_logged_in)
def user_login_notify(sender, **kwargs):
    """
    For testing purposes: Just sent a notification MijnGemeente about a user
    login.
    """

    # Just skip this for now..
    return

    user = kwargs.get('user')

    kwargs = {
        'title': f'{user.username} is ingelogd!',
        'body': None,
        'reference': f'user-{user.pk}',
        'url': reverse('admin:accounts_user_change', args=(user.pk, )),
    }

    UserNotification.create_and_notify(**kwargs)
