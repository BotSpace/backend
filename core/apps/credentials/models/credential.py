from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.apps.credentials.registry import get_type


class Credential(models.Model):
    """Encrypted credential instance — owner-scoped, usable across all projects."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="credentials",
        verbose_name=_("owner"),
    )
    # Registry key — validated against CREDENTIAL_TYPES in registry.py
    type_key = models.CharField(max_length=40, verbose_name=_("type key"))
    name = models.CharField(max_length=120, verbose_name=_("name"))
    # Fernet-encrypted JSON dict of field values
    data_encrypted = models.TextField(verbose_name=_("data encrypted"))

    # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("deleted at"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "credential"
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="credential_unique_name_per_owner",
            )
        ]
        indexes = [
            models.Index(fields=["owner", "deleted_at"], name="credential_owner_deleted_idx"),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.owner_id}:{self.name}"

    @property
    def is_alive(self) -> bool:
        return self.deleted_at is None

    @property
    def type_info(self) -> dict | None:
        """Resolved registry entry for this credential's type_key."""
        return get_type(self.type_key)
