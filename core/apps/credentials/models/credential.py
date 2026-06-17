from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Credential(models.Model):
    """Encrypted credential instance bound to a project."""

    project = models.ForeignKey(
        "api.ProjectModel",
        on_delete=models.CASCADE,
        related_name="credentials",
        verbose_name=_("project"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_credentials",
        verbose_name=_("owner"),
    )
    type = models.ForeignKey(
        "credentials.CredentialType",
        on_delete=models.PROTECT,
        related_name="credentials",
        verbose_name=_("type"),
    )
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
                fields=["project", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="credential_unique_name_per_project",
            )
        ]
        indexes = [
            models.Index(fields=["project", "deleted_at"]),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.project_id}:{self.name}"

    @property
    def is_alive(self) -> bool:
        return self.deleted_at is None
