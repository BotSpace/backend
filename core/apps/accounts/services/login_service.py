from django.utils import timezone
from core.apps.shared.observability.metrics import safe_inc, USER_LOGINS


def record_login(user, method: str) -> None:
    """Create a LoginLog entry, increment the Prometheus counter, and refresh last_login."""
    from core.apps.accounts.models import LoginLog  # avoid circular import

    LoginLog.objects.create(user=user, method=method)
    safe_inc(USER_LOGINS, method=method)
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
