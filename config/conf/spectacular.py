"""drf-spectacular configuration.

Adds tags, contact info, standard error responses, and a postprocessing
hook that:
  * wraps every 2xx response into the canonical ``{status, data}`` shape, and
  * injects a standard error schema reference into every 4xx/5xx response.
"""

from __future__ import annotations

SPECTACULAR_SETTINGS = {
    "TITLE": "BotMother API",
    "DESCRIPTION": (
        "BotMother backend public API. All endpoints live under `/api/v1/`. "
        "Legacy `/api/` and root paths are deprecated and emit "
        "`Deprecation`/`Sunset` response headers; clients should migrate "
        "before the sunset date."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CAMELIZE_NAMES": True,
    "COMPONENT_SPLIT_REQUEST": True,
    "POSTPROCESSING_HOOKS": ["config.conf.spectacular.custom_postprocessing_hook"],
    "SERVERS": [{"url": "/api/v1", "description": "Stable v1"}],
    "CONTACT": {"name": "BotSpace Engineering", "email": "engineering@botspace.uz"},
    "LICENSE": {"name": "Proprietary"},
    "TAGS": [
        {"name": "auth", "description": "Registration, login, token rotation."},
        {"name": "me", "description": "Authenticated user profile."},
        {"name": "project", "description": "Bot projects (CRUD + deploy + dashboard)."},
        {"name": "relase", "description": "Release versions of a project."},
        {"name": "plan", "description": "Subscription plans and limits."},
        {"name": "payment", "description": "Transactions, history, webhooks (Click, Payme, PayTech)."},
        {"name": "template", "description": "Marketplace templates: list, purchase, submit."},
        {"name": "cms", "description": "MongoDB-backed collections per project."},
        {"name": "health", "description": "Liveness and readiness probes (unauthenticated)."},
    ],
    "ENUM_NAME_OVERRIDES": {
        "ContainerStatusEnum": "core.apps.api.enums.container.ContainerStatusEnum",
    },
}


_ERROR_SCHEMA = {
    "type": "object",
    "required": ["status", "detail"],
    "properties": {
        "status": {"type": "boolean", "example": False},
        "detail": {"type": "string", "example": "Authentication credentials were not provided."},
        "errors": {
            "type": "object",
            "additionalProperties": True,
            "description": "Field-level validation errors when applicable.",
        },
        "incident_id": {
            "type": "string",
            "description": "Server-generated id for 500 responses; quote it when reporting bugs.",
        },
    },
}


def custom_postprocessing_hook(result, generator, request, public):
    """Wrap 2xx responses in ``{status, data}`` and standardise errors."""
    for path, methods in result.get("paths", {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            for status_code, response in operation["responses"].items():
                if not isinstance(response, dict):
                    continue
                content = response.get("content", {})
                if status_code in {"200", "201", "202"}:
                    for content_type, body in content.items():
                        original_schema = body.get("schema", {})
                        body["schema"] = {
                            "type": "object",
                            "required": ["status", "data"],
                            "properties": {
                                "status": {"type": "boolean", "example": True},
                                "data": original_schema,
                            },
                        }
                elif status_code.startswith(("4", "5")):
                    response.setdefault("content", {})
                    for content_type in ("application/json",):
                        response["content"].setdefault(content_type, {})["schema"] = _ERROR_SCHEMA
    return result
