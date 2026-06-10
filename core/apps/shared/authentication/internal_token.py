"""DRF authentication: system-to-system token + on-behalf-of user id.

The agent verifies the user's JWT locally (it already has the JWT
public key) and then calls backend endpoints using its internal token
plus an X-User-Id header. This stops us from forwarding short-lived
user JWTs across the cluster and removes the access-token refresh
roundtrip from every agent run.

Header contract:
  X-Internal-Token: <settings.INTERNAL_API_TOKEN>
  X-User-Id:        <numeric user id whose context this request runs in>

Falls through (returns None) on any mismatch so DRF can still try
JWTAuthentication. A wrong internal token does NOT 401 here — the
next auth class can still accept a regular Bearer JWT.
"""

from __future__ import annotations

import hmac

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()


class InternalTokenAuthentication(authentication.BaseAuthentication):
    keyword = "X-Internal-Token"

    def authenticate(self, request):
        internal_token = request.META.get("HTTP_X_INTERNAL_TOKEN")
        if not internal_token:
            return None
        expected = getattr(settings, "INTERNAL_API_TOKEN", None)
        if not expected or not hmac.compare_digest(str(internal_token), str(expected)):
            # Wrong token -> let the next auth class decide. We don't
            # want to leak whether the token format is recognized.
            # compare_digest is constant-time (no timing oracle).
            return None
        user_id = request.META.get("HTTP_X_USER_ID")
        if not user_id:
            raise exceptions.AuthenticationFailed(
                "X-Internal-Token requires X-User-Id header"
            )
        try:
            user = User.objects.get(pk=int(user_id))
        except (User.DoesNotExist, ValueError, TypeError) as exc:
            raise exceptions.AuthenticationFailed(
                f"X-User-Id {user_id!r} not found"
            ) from exc
        return (user, None)

    def authenticate_header(self, request):
        # Hint sent on 401 — keeps Bearer as the primary scheme so
        # browsers still prompt correctly.
        return 'Bearer realm="api"'
