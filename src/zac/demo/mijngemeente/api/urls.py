from django.urls import path

from .views import CallbackView

urlpatterns = [
    path('callbacks', CallbackView.as_view(), name='mijngemeente-notificaties-webhook'),
]
