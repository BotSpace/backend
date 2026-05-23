from __future__ import annotations

from django.conf import settings
from django.db import models

from core.apps.cms.enums import AuditAction


class AuditLog(models.Model):
    """Audit trail — every schema/document change is persisted here.

    For document-level actions, `document_id` holds the Mongo ObjectId (hex).
    """

    collection = models.ForeignKey(
        "cms.Collection",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cms_audits",
    )
    action = models.CharField(max_length=24, choices=AuditAction.choices)
    document_id = models.CharField(max_length=64, blank=True, default="")
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cms_audit_log"
        indexes = [
            models.Index(fields=["collection", "-created_at"]),
            models.Index(fields=["collection", "document_id"]),
            models.Index(fields=["action"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.collection_id}/{self.document_id}"
