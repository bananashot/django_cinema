from django.apps import AppConfig


class CinemaAppConfig(AppConfig):
    name = 'cinema_app'

    def ready(self):
        import cinema_app.signals
