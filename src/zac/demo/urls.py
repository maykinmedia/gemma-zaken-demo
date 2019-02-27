from django.urls import include, path
from django.views.generic import RedirectView

app_name = 'demo'
urlpatterns = [
    path('', RedirectView.as_view(url='../')),
    path('mor/', include('zac.demo.mor.urls')),
    path('zaakbeheer/', include('zac.demo.zaakbeheer.urls')),
    path('opendata/', include('zac.demo.opendata.urls')),
    path('archiveren/', include('zac.demo.archiveren.urls')),
    path('selectielijst', include('zac.demo.selectielijst.urls')),
]
