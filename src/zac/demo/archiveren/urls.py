from django.urls import path

from . import views

urlpatterns = [
    path('', views.ArchiverenListView.as_view(), name='archiveren-index'),
    path('<slug:uuid>/', views.ArchiverenDetailView.as_view(), name='archiveren-detail'),
    # path('<slug:uuid>/status/toevoegen/', views.StatusCreateView.as_view(), name='zaakbeheer-statuscreate'),
    # path('<slug:uuid>/besluit/toevoegen/', views.BesluitCreateView.as_view(), name='zaakbeheer-besluitcreate'),
]
