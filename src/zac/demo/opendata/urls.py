from django.urls import path

from . import views

urlpatterns = [
    path('', views.ZaakMapView.as_view(), name='opendata-index'),
]
