from django.apps import AppConfig


class MijnGemeenteAppConfig(AppConfig):
    name = 'zac.demo.mijngemeente'

    def ready(self):
        from . import signals
