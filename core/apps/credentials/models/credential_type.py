from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CredentialType(models.Model):
    """Credential type schema definition.

    Built-in types (system=True, owner=None) are seeded via data migration.
    Users can add custom types (system=False, owner=<user>).
    """

    class Mode(models.TextChoices):
        APIKEY = "apikey", _("API Key")
        BEARER = "bearer", _("Bearer Token")
        HEADER = "header", _("Header Auth")
        BASIC = "basic", _("Basic Auth")
        NONE = "none", _("None")

    key = models.SlugField(max_length=80, unique=True, verbose_name=_("key"))
    label = models.CharField(max_length=120, verbose_name=_("label"))
    description = models.TextField(blank=True, default="", verbose_name=_("description"))
    icon = models.CharField(max_length=64, blank=True, default="", verbose_name=_("icon"))
    mode = models.CharField(max_length=16, choices=Mode.choices, verbose_name=_("mode"))
    # List of field descriptors: [{name, label, type, secret, required, default, options}, ...]
    fields = models.JSONField(default=list, blank=True, verbose_name=_("fields"))
    system = models.BooleanField(default=False, verbose_name=_("system"))
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credential_types",
        verbose_name=_("owner"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "credential_type"
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key} ({self.mode})"
