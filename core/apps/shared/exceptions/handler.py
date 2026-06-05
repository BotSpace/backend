"""Project-wide DRF exception handler.

Normalises every response body to ``{"status": false, "detail": …,
"errors": …}`` so clients never have to guess the shape. Internal
errors are logged with the traceback while the response stays
opaque to avoid leaking stack frames.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger(__name__)

# Import lazily to avoid circular imports at module load time.
def _get_running_bot_limit_exc():
    from core.apps.api.exceptions.running_bot_limit import RunningBotLimitExceeded  # noqa: PLC0415
    return RunningBotLimitExceeded


def custom_exception_handler(exc: Exception, context: dict[str, Any]):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    if isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    RunningBotLimitExceeded = _get_running_bot_limit_exc()
    if isinstance(exc, RunningBotLimitExceeded):
        return Response(
            {
                "status": False,
                "detail": str(exc.detail),
                "code": exc.default_code,
                "limit": exc.limit,
                "running": exc.running,
            },
            status=exc.status_code,
        )

    response = drf_default_handler(exc, context)
    if response is not None:
        response.data = _shape(exc, response.data)
        return response

    incident_id = uuid.uuid4().hex[:12]
    logger.exception("Unhandled exception (incident=%s): %r", incident_id, exc)
    return Response(
        {
            "status": False,
            "detail": "Internal server error",
            "incident_id": incident_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _extract_codes(data: Any) -> Any:
    """Walk DRF error structure and pull `ErrorDetail.code` into a parallel
    tree of `{field: [code, ...]}`.

    Keeps stable, machine-readable identifiers (e.g. ``paid_plan_required``)
    alongside the human messages so SDK callers and the AI agent can branch
    on them without scraping localized strings.
    """
    if isinstance(data, ErrorDetail):
        return data.code
    if isinstance(data, dict):
        return {k: _extract_codes(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_extract_codes(x) for x in data]
    return None


def _shape(exc: Exception, data: Any) -> Any:
    codes = _extract_codes(data) if isinstance(exc, exceptions.ValidationError) else None
    if isinstance(data, dict) and "status" in data:
        return data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        out = {"status": False, "detail": data["detail"]}
        if isinstance(data["detail"], ErrorDetail) and data["detail"].code:
            out["code"] = data["detail"].code
        return out
    if isinstance(data, dict):
        out = {"status": False, "detail": exc.__class__.__name__, "errors": data}
        if codes:
            out["codes"] = codes
        return out
    if isinstance(data, list):
        out = {"status": False, "detail": exc.__class__.__name__, "errors": data}
        if codes:
            out["codes"] = codes
        return out
    return {"status": False, "detail": str(data)}
