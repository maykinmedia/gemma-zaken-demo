from django.urls import path

from . import views

urlpatterns = [
    path('', views.ConfigView.as_view(), name='config-index'),
]
