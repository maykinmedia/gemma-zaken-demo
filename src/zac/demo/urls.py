from django.urls import path, include

app_name = 'demo'
urlpatterns = [
    path('mor/', include('zac.demo.mor.urls')),
    path('zaakbeheer/', include('zac.demo.zaakbeheer.urls'))
]
