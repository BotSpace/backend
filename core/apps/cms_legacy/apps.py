from django.apps import AppConfig


class ModuleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.apps.cms_legacy"
    label = "cms_legacy"
    verbose_name = "CMS (legacy)"

    def ready(self) -> None:
        try:
            import core.apps.cms_legacy.signals  # noqa: F401
        except ImportError:
            pass
