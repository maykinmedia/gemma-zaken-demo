from django.urls import path

from . import views

urlpatterns = [
    path('', views.MORCreateView.as_view(), name='mor-index'),
    path('thanks/', views.MORThanksView.as_view(), name='mor-thanks'),
]
