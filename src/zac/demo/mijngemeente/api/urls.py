from django.urls import path

from vng_api_common.notifications.api.views import NotificationView

urlpatterns = [
    path('callbacks', NotificationView.as_view(), name='mijngemeente-notificaties-webhook'),
]
