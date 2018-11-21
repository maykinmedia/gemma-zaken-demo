from django.urls import path

from . import views

urlpatterns = [
    path('', views.ZaakListView.as_view(), name='zaakbeheer-index'),
    path('<slug:uuid>/', views.ZaakDetailView.as_view(), name='zaakbeheer-detail'),
    path('<slug:uuid>/status/toevoegen/', views.ZaakStatusCreateView.as_view(), name='zaakbeheer-statuscreate'),
]
