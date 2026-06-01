from django.db import models
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel


class Config(AbstractBaseModel):
    """
    Global key-value store for runtime configuration.

    Admin-editable from the Django admin panel or via the admin CRUD API.
    Public (is_public=True) entries are served unauthenticated at
    GET /api/v1/shared/config/public/ for consumption by the AI agent
    and other services.
    """

    key = models.CharField(_("key"), max_length=255, unique=True, db_index=True)
    value = models.JSONField(_("value"), default=None, null=True, blank=True)
    label = models.CharField(_("label"), max_length=255, blank=True)
    group = models.CharField(_("group"), max_length=100, blank=True, db_index=True)
    is_public = models.BooleanField(_("is public"), default=True)
    description = models.TextField(_("description"), blank=True)

    class Meta:
        db_table = "global_config"
        verbose_name = _("Config")
        verbose_name_plural = _("Configs")
        ordering = ["group", "key"]

    def __str__(self) -> str:
        return f"{self.group}.{self.key}" if self.group else self.key
