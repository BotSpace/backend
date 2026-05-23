from __future__ import annotations

from django.db import models

from core.apps.cms.enums import WebhookEvent


class Webhook(models.Model):
    """Outbound webhook fired on document/schema events."""

    collection = models.ForeignKey(
        "cms.Collection",
        on_delete=models.CASCADE,
        related_name="webhooks",
    )
    name = models.CharField(max_length=120, blank=True, default="")
    url = models.URLField(max_length=500)
    event = models.CharField(max_length=32, choices=WebhookEvent.choices)
    secret = models.CharField(max_length=128, blank=True, default="")
    headers = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)

    last_status = models.CharField(max_length=16, blank=True, default="")
    last_response = models.TextField(blank=True, default="")
    last_fired_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cms_webhook"
        indexes = [
            models.Index(fields=["collection", "event", "active"]),
        ]

    def __str__(self) -> str:
        return f"{self.collection_id}:{self.event} → {self.url}"
