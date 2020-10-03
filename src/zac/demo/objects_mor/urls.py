from django.urls import path

from . import views

urlpatterns = [
    path('', views.ObjectMorCreateView.as_view(), name='objects-mor-index'),
    path('thanks/', views.ObjectMorThanksView.as_view(), name='objects-mor-thanks'),
]
