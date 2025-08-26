from django.apps import AppConfig

class BlogcConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blogc'

    def ready(self):
        from . import signals
