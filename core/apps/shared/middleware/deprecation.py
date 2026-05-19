"""Middleware that marks legacy (non-versioned) API paths as deprecated."""

from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse


class LegacyApiDeprecationMiddleware:
    """Adds RFC 8594 ``Deprecation`` and ``Sunset`` headers to legacy API
    responses.

    Any URL that starts with ``/api/`` *but* not with ``/api/v1/`` is
    considered legacy. Health, admin, and static paths are untouched.
    """

    LEGACY_PREFIX = "/api/"
    V1_PREFIX = "/api/v1/"
    SUNSET = "Wed, 31 Dec 2026 23:59:59 GMT"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        path = request.path
        if path.startswith(self.LEGACY_PREFIX) and not path.startswith(self.V1_PREFIX):
            response["Deprecation"] = "true"
            response["Sunset"] = self.SUNSET
            response["Link"] = f'<{self.V1_PREFIX.rstrip("/")}>; rel="successor-version"'
        return response
