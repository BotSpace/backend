"""Credential type registry — types are defined in CODE, not in the DB.

Adding a new type = appending one dict to CREDENTIAL_TYPES.
No DB table, no API to create/edit types.
"""
from __future__ import annotations

CREDENTIAL_TYPES: list[dict] = [
    {
        "key": "api_key",
        "label": "API Key / Token",
        "icon": "key",
        "mode": "apikey",
        "fields": [
            {"name": "token", "label": "API Key / Token", "type": "password", "secret": True, "required": True},
            {"name": "param_name", "label": "Header / query name", "type": "text", "required": True, "default": "X-API-Key"},
            {
                "name": "placement",
                "label": "Joylashuv",
                "type": "select",
                "required": True,
                "default": "header",
                "options": [
                    {"value": "header", "label": "Header"},
                    {"value": "query", "label": "Query param"},
                ],
            },
        ],
    },
    {
        "key": "bearer",
        "label": "Bearer Token",
        "icon": "shield",
        "mode": "bearer",
        "fields": [
            {"name": "token", "label": "Token", "type": "password", "secret": True, "required": True},
        ],
    },
    {
        "key": "header_auth",
        "label": "Header Auth",
        "icon": "list",
        "mode": "header",
        "fields": [
            {"name": "header_name", "label": "Header nomi", "type": "text", "required": True, "default": "Authorization"},
            {"name": "header_value", "label": "Header qiymati", "type": "password", "secret": True, "required": True},
        ],
    },
    {
        "key": "basic_auth",
        "label": "Basic Auth",
        "icon": "user",
        "mode": "basic",
        "fields": [
            {"name": "username", "label": "Username", "type": "text", "required": True},
            {"name": "password", "label": "Password", "type": "password", "secret": True, "required": True},
        ],
    },
    # --- placeholder types (structure ready; exact fields TBD later) ---
    {
        "key": "telegram",
        "label": "Telegram",
        "icon": "send",
        "mode": "none",
        "fields": [
            {"name": "bot_token", "label": "Bot token", "type": "password", "secret": True, "required": True},
        ],
        "todo": "final fields TBD (account/session?)",
    },
    {
        "key": "google",
        "label": "Google",
        "icon": "globe",
        "mode": "none",
        "fields": [
            {"name": "api_key", "label": "API key", "type": "password", "secret": True, "required": True},
        ],
        "todo": "final fields TBD (OAuth account?)",
    },
]

_TYPE_MAP: dict[str, dict] = {t["key"]: t for t in CREDENTIAL_TYPES}


def get_type(key: str) -> dict | None:
    """Return the type dict for *key*, or None if not found."""
    return _TYPE_MAP.get(key)


def list_types() -> list[dict]:
    """Return all registered credential types."""
    return list(CREDENTIAL_TYPES)
