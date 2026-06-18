"""Credential type registry — types are defined in CODE, not in the DB.

Adding a new type = appending one dict to CREDENTIAL_TYPES.
No DB table, no API to create/edit types.
"""
from __future__ import annotations

# Each type is purpose-specific (a service), not a generic auth scheme. If a service needs
# basic/bearer/api-key auth, that is baked into the type's `mode` + fields below.
# `color` drives the (colored) icon in the UI.
CREDENTIAL_TYPES: list[dict] = [
    # --- AI providers ---
    {
        "key": "openai",
        "label": "ChatGPT (OpenAI)",
        "icon": "bot",
        "color": "#10A37F",
        "mode": "bearer",
        "fields": [
            {"name": "api_key", "label": "API key", "type": "password", "secret": True, "required": True},
            {"name": "base_url", "label": "Base URL", "type": "text", "required": False, "default": "https://api.openai.com/v1"},
        ],
    },
    {
        "key": "ai_studio",
        "label": "Google AI Studio",
        "icon": "sparkles",
        "color": "#1A73E8",
        "mode": "bearer",
        "fields": [
            {"name": "api_key", "label": "API key", "type": "password", "secret": True, "required": True},
        ],
    },
    {
        "key": "ollama",
        "label": "Ollama",
        "icon": "boxes",
        "color": "#F97316",
        "mode": "bearer",
        "fields": [
            {"name": "base_url", "label": "Base URL", "type": "text", "required": True, "default": "https://ollama.com/v1"},
            {"name": "api_key", "label": "API key", "type": "password", "secret": True, "required": False},
        ],
    },
    # --- Search tools ---
    {
        "key": "tavily",
        "label": "Tavily Search",
        "icon": "search",
        "color": "#6E56CF",
        "mode": "bearer",
        "fields": [
            {"name": "api_key", "label": "API key", "type": "password", "secret": True, "required": True},
            {"name": "base_url", "label": "Base URL", "type": "text", "required": False, "default": "https://api.tavily.com"},
        ],
    },
    # --- Messaging ---
    {
        "key": "telegram",
        "label": "Telegram",
        "icon": "send",
        "color": "#229ED9",
        "mode": "none",
        "fields": [
            {"name": "bot_token", "label": "Bot token", "type": "password", "secret": True, "required": True},
        ],
    },
    # --- OAuth2 types (Google) ---
    {
        "key": "google_email",
        "label": "Google (Email)",
        "icon": "mail",
        "color": "#EA4335",
        "mode": "oauth2",
        "provider": "google",
        "scopes": [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        "fields": [],
    },
    {
        "key": "google_sheets",
        "label": "Google Sheets",
        "icon": "table",
        "color": "#0F9D58",
        "mode": "oauth2",
        "provider": "google",
        "scopes": [
            "openid",
            "email",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
        "fields": [],
    },
    {
        "key": "google_drive",
        "label": "Google Drive",
        "icon": "folder",
        "color": "#FBBC04",
        "mode": "oauth2",
        "provider": "google",
        "scopes": [
            "openid",
            "email",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
        "fields": [],
    },
]

_TYPE_MAP: dict[str, dict] = {t["key"]: t for t in CREDENTIAL_TYPES}


def get_type(key: str) -> dict | None:
    """Return the type dict for *key*, or None if not found."""
    return _TYPE_MAP.get(key)


def list_types() -> list[dict]:
    """Return all registered credential types (including provider/scopes for oauth2)."""
    return list(CREDENTIAL_TYPES)
