from django.apps import AppConfig

from zds_client import Client


class SelectielijstAppConfig(AppConfig):
    name = 'zac.demo.selectielijst'

    def ready(self):
        Client.load_config(vrl={
            'scheme': 'https',
            'host': 'ref.tst.vng.cloud',
            'port': 443,
            'auth': None,
        })
