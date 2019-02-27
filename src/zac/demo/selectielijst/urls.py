from django.urls import path

from .views import SelectieLijstProcestypenView

urlpatterns = [
    path('procestypen', SelectieLijstProcestypenView.as_view(), name='selectielijst-index'),
]
