from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.ZaakListView.as_view(), name='mijngemeente-index'),
    path('api/', include('zac.demo.mijngemeente.api.urls')),
    # path('<slug:uuid>/', views.ZaakDetailView.as_view(), name='mijngemeente-detail'),
]
