from django.urls import path

from . import views

urlpatterns = [
    path('', views.ObjectMapView.as_view(), name='objectdata-index'),
]
