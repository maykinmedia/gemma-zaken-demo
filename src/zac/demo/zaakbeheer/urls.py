from django.urls import path

from . import views

urlpatterns = [
    path('', views.ZaakListView.as_view(), name='zaakbeheer-index'),
    path('<slug:uuid>/', views.ZaakDetailView.as_view(), name='zaakbeheer-detail'),
    path('<slug:uuid>/status/toevoegen/', views.StatusCreateView.as_view(), name='zaakbeheer-statuscreate'),
    path('<slug:uuid>/besluit/toevoegen/', views.BesluitCreateView.as_view(), name='zaakbeheer-besluitcreate'),
    path('<slug:uuid>/resultaat/', views.ResultaatEditView.as_view(), name='zaakbeheer-resultaatedit'),
]
