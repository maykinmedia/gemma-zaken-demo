from django.urls import path

from .views import ResultatenListView, SelectieLijstProcestypenListView

urlpatterns = [
    path('procestypen', SelectieLijstProcestypenListView.as_view(), name='selectielijst-index'),
    path('resultaten', ResultatenListView.as_view(), name='selectielijst-resultaten'),
]
