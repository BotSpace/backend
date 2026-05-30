# type: ignore
"""Re-export the global IsAdminUser so admin views import locally."""

from core.permissions.engine import IsAdminUser

__all__ = ["IsAdminUser"]
