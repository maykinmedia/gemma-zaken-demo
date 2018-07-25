from django.urls import path

from . import views

urlpatterns = [
    path('', views.ZaakListView.as_view(), name='zaakbeheer-index'),
]
