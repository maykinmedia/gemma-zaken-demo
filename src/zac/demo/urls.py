from django.urls import include, path

app_name = 'demo'
urlpatterns = [
    path('mor/', include('zac.demo.mor.urls')),
    path('zaakbeheer/', include('zac.demo.zaakbeheer.urls'))
]
