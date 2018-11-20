from django.urls import path

from . import views

urlpatterns = [
    path('', views.StatusView.as_view(), name='status-index'),
]
