"""Permission class for system-to-system endpoints that only need X-Internal-Token.

Unlike InternalTokenAuthentication (which also requires X-User-Id), this
permission class is designed for endpoints that have no user context at all —
e.g. the config /internal/ endpoint read by the AI agent service.

Usage:
    @action(permission_classes=[IsInternalTokenOnly], ...)
    def internal(self, request): ...

Returns HTTP 401 when the header is absent or does not match settings.INTERNAL_API_TOKEN.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed


class IsInternalTokenOnly(permissions.BasePermission):
    """Allow access only when X-Internal-Token matches settings.INTERNAL_API_TOKEN.

    Does NOT require X-User-Id — suitable for pure service-to-service calls
    with no user context.
    """

    message = "Invalid or missing X-Internal-Token."

    def has_permission(self, request, view) -> bool:
        expected = getattr(settings, "INTERNAL_API_TOKEN", None)
        if not expected:
            # Token not configured on this instance — deny to avoid leaking data.
            raise AuthenticationFailed(self.message)
        provided = request.META.get("HTTP_X_INTERNAL_TOKEN", "")
        if not provided or provided != expected:
            raise AuthenticationFailed(self.message)
        return True
