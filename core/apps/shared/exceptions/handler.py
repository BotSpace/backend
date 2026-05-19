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
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict[str, Any]):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    if isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

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


def _shape(exc: Exception, data: Any) -> Any:
    if isinstance(data, dict) and "status" in data:
        return data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        return {"status": False, "detail": data["detail"]}
    if isinstance(data, dict):
        return {"status": False, "detail": exc.__class__.__name__, "errors": data}
    if isinstance(data, list):
        return {"status": False, "detail": exc.__class__.__name__, "errors": data}
    return {"status": False, "detail": str(data)}
