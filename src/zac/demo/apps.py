from django.apps import AppConfig


class DemoConfig(AppConfig):
    name = 'zac.demo'

    def ready(self):
        from . import signals

        signals.initialize_settings()
