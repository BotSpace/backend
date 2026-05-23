"""Outbound webhook dispatch — best effort, async via Celery if available."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import requests

from core.apps.cms.enums import WebhookEvent
from core.apps.cms.models import Collection, Webhook


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _dispatch_sync(webhook: Webhook, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, default=str).encode("utf-8")
    headers = {"Content-Type": "application/json", **(webhook.headers or {})}
    if webhook.secret:
        headers["X-Cmsv2-Signature"] = _sign(webhook.secret, body)
    try:
        resp = requests.post(webhook.url, data=body, headers=headers, timeout=8)
        webhook.last_status = str(resp.status_code)
        webhook.last_response = (resp.text or "")[:2000]
        webhook.failure_count = 0 if resp.ok else webhook.failure_count + 1
    except Exception as exc:
        webhook.last_status = "error"
        webhook.last_response = str(exc)[:2000]
        webhook.failure_count += 1
    from django.utils import timezone

    webhook.last_fired_at = timezone.now()
    webhook.save(update_fields=["last_status", "last_response", "failure_count", "last_fired_at"])


def fire(collection: Collection, event: WebhookEvent | str, payload: dict[str, Any]) -> None:
    hooks = Webhook.objects.filter(collection=collection, event=str(event), active=True)
    for hook in hooks:
        # Synchronous; future iteration can hand this off to Celery.
        _dispatch_sync(hook, {"event": str(event), "collection": collection.name, **payload})
