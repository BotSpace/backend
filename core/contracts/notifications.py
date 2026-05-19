"""Notification service contract."""

from __future__ import annotations

from typing import Protocol


class NotificationService(Protocol):
    """Out-of-band user notifications (email, SMS, Telegram)."""

    def notify(self, user, *, subject: str, message: str, channel: str = "auto") -> bool:
        ...
