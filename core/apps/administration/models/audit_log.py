# type: ignore
"""AdminAuditLogModel — append-only record of every destructive admin action.

Written by `core.apps.administration.services.audit.log_admin_action` from
each admin endpoint after the database change commits. The model is
intentionally denormalised — no FK to the target object, just a string
type + id — so deleting a target later doesn't drop its history.
"""

from django.contrib.auth import get_user_model
from django.db import models
from django_core.models import AbstractBaseModel

User = get_user_model()


class AdminAuditLogModel(AbstractBaseModel):
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="admin_audit_logs",
        verbose_name="Actor (admin user)",
    )
    action = models.CharField(
        max_length=120,
        help_text=(
            "Dotted code: domain.verb (user.ban, user.balance_set, "
            "template.verify, withdrawal.approve, withdrawal.reject, "
            "plan.create, plan.update, plan.delete, ticket.respond, ...)"
        ),
    )
    target_type = models.CharField(max_length=60, blank=True, default="")
    target_id = models.CharField(max_length=60, blank=True, default="")
    payload_before = models.JSONField(null=True, blank=True)
    payload_after = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "admin_audit_log"
        verbose_name = "Admin audit log entry"
        verbose_name_plural = "Admin audit log"
        ordering = ("-id",)
        indexes = [
            models.Index(fields=["actor", "-id"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["action", "-id"]),
        ]

    def __str__(self) -> str:
        actor = getattr(self.actor, "phone", None) or getattr(self.actor, "email", None) or "?"
        return f"{actor} → {self.action} ({self.target_type}:{self.target_id})"
