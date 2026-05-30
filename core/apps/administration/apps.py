from django.apps import AppConfig


class ModuleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.apps.administration"
    verbose_name = "Administration (admin panel REST API)"
