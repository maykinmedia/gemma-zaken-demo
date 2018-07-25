from django.apps import AppConfig


class DemoMORConfig(AppConfig):
    name = 'zac.demo.mor'

    def ready(self):
        from . import signals