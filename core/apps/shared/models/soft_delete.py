"""Soft-delete mixin + manager.

Adds a ``deleted_at`` timestamp instead of hard-deleting rows so we
keep an audit trail and can recover accidentally-deleted records.
Use :class:`SoftDeleteModel` as a base for any model that should
support soft delete; default manager hides soft-deleted rows. Access
all rows (including deleted) via ``Model.all_objects``.
"""

from __future__ import annotations

from typing import Optional

from django.db import models
from django.utils import timezone
from django_core.models import AbstractBaseModel


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):  # type: ignore[override]
        return super().update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):  # type: ignore[misc]
    """Hides soft-deleted rows by default."""

    def __init__(self, *args, include_deleted: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._include_deleted = include_deleted

    def get_queryset(self) -> SoftDeleteQuerySet:
        qs = super().get_queryset()
        if not self._include_deleted:
            qs = qs.filter(deleted_at__isnull=True)
        return qs


class SoftDeleteModel(AbstractBaseModel):
    """Adds a nullable ``deleted_at`` field and soft-delete semantics."""

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteManager(include_deleted=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents: bool = False, hard: bool = False):  # type: ignore[override]
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
        return 1, {self._meta.label: 1}

    def restore(self) -> None:
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
