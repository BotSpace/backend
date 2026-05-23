from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Collection(models.Model):
    """Cmsv2 collection (schema). Documents themselves live in MongoDB."""

    project = models.ForeignKey(
        "api.ProjectModel",
        on_delete=models.CASCADE,
        related_name="cms_collections",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cms_owned_collections",
    )
    name = models.SlugField(
        verbose_name=_("name"),
        max_length=80,
        help_text="MongoDB collection name (lowercase, snake_case).",
    )
    label = models.CharField(max_length=120, blank=True, default="")
    description = models.TextField(blank=True, default="")

    # System collections (users, chat) cannot be deleted from the UI.
    system = models.BooleanField(default=False)

    # Schema version — bumps on every field add/remove/update.
    schema_version = models.PositiveIntegerField(default=1)

    # Soft delete
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cms_collection"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="cms_collection_unique_per_project",
            )
        ]
        indexes = [
            models.Index(fields=["project", "deleted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.project_id}:{self.name}"

    @property
    def is_alive(self) -> bool:
        return self.deleted_at is None

    @property
    def can_delete(self) -> bool:
        return not self.system
