from django.apps import AppConfig


class ModuleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.apps.cms"
    verbose_name = "CMS"

    def ready(self) -> None:
        try:
            import core.apps.cms.signals  # noqa: F401
        except ImportError:
            pass
