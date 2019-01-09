import json

from factory.django import DjangoModelFactory as Dmf
from zac.accounts.models import User
from ...models import SiteConfiguration


class UserFactory(Dmf):

    class Meta:
        model = User

    username = 'test'
    password = 'test1234'


class SiteConfigurationFactory(Dmf):
    class Meta:
        model = SiteConfiguration

    ztc_catalogus_uuid = 'f7afd156-c8f5-4666-b8b5-28a4a9b5dfc7'
    global_api_client_id = 'demo-app-KK2CG69NTrSN'
    global_api_secret = 'wo1hW8oHsM0U9hSTnMM0jtCbD8GYmf4i'
    google_api_key = 'AIzaSyA1fl_5ChJEHYi0Vn1r7IOu2kAP3hQTLlE'
    ztc_mor_zaaktype_uuid = '0119dd4e-7be9-477e-bccf-75023b1453c1'
