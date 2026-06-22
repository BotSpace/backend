"""Credential type registry — three sources: code, admin (Config JSON), module (manifest_cache).

Priority on key collision: code > admin > module.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

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

_CODE_TYPE_MAP: dict[str, dict] = {t["key"]: t for t in CREDENTIAL_TYPES}

# Config key where admin-created custom types are stored as a JSON list.
ADMIN_CONFIG_KEY = "credentials.custom_types"

VALID_FIELD_TYPES = {"text", "password", "number", "textarea", "select", "url", "switch"}
VALID_MODES = {"bearer", "apikey", "basic", "header", "oauth2", "none"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_admin_types() -> list[dict]:
    """Load admin-created types from Config JSON store. Returns [] on any error."""
    try:
        from core.apps.shared.models import Config  # local import — avoids circular at module load
        cfg = Config.objects.filter(key=ADMIN_CONFIG_KEY).first()
        if cfg is None or not cfg.value:
            return []
        types = cfg.value if isinstance(cfg.value, list) else []
        return [t for t in types if isinstance(t, dict) and t.get("key")]
    except Exception as exc:
        logger.warning("registry: failed to load admin credential types: %s", exc)
        return []


def _get_module_types() -> list[dict]:
    """Collect credentialTypes from all enabled modules' manifest_cache.

    Returns a flat list of (slug, type_dict) — duplicates across modules are unlikely
    because keys are namespaced with the module slug.
    """
    try:
        from core.apps.api.models.module import ModuleModel  # local import
        result = []
        for module in ModuleModel.objects.filter(active=True):
            cache = module.manifest_cache or {}
            for ct in cache.get("credential_types", []):
                if not isinstance(ct, dict) or not ct.get("key"):
                    continue
                result.append((module.slug, ct))
        return result
    except Exception as exc:
        logger.warning("registry: failed to load module credential types: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_type(key: str) -> dict | None:
    """Return the type dict for *key* from any source (code > admin > module), or None."""
    # 1. code
    if key in _CODE_TYPE_MAP:
        return _CODE_TYPE_MAP[key]
    # 2. admin
    for t in _get_admin_types():
        if t.get("key") == key:
            return t
    # 3. module
    for _slug, t in _get_module_types():
        if t.get("key") == key:
            return t
    return None


def list_types(request=None) -> list[dict]:
    """Return all registered credential types from all three sources.

    Each type gains two extra fields:
      source   — "code" | "admin" | "module:<slug>"
      editable — True only for admin types

    Priority / dedup: code keys win over admin, admin over module.
    The `request` parameter is accepted for future per-user module filtering
    but is currently unused (all active-module types are included).
    """
    seen: dict[str, dict] = {}

    # 1. code
    for t in CREDENTIAL_TYPES:
        entry = dict(t, source="code", editable=False)
        seen[t["key"]] = entry

    # 2. admin
    for t in _get_admin_types():
        k = t.get("key")
        if not k or k in seen:
            continue
        seen[k] = dict(t, source="admin", editable=True)

    # 3. module
    for slug, t in _get_module_types():
        k = t.get("key")
        if not k or k in seen:
            continue
        seen[k] = dict(t, source=f"module:{slug}", editable=False)

    return list(seen.values())


# ---------------------------------------------------------------------------
# Admin type CRUD helpers (used by the API view)
# ---------------------------------------------------------------------------

def _load_admin_config():
    """Return (Config instance or None, current list)."""
    from core.apps.shared.models import Config
    cfg, _ = Config.objects.get_or_create(
        key=ADMIN_CONFIG_KEY,
        defaults={
            "label": "Custom credential types",
            "group": "credentials",
            "is_public": False,
            "value": [],
        },
    )
    types = cfg.value if isinstance(cfg.value, list) else []
    return cfg, types


def admin_create_type(data: dict) -> dict:
    """Append a new admin type. Raises ValueError on key collision."""
    cfg, types = _load_admin_config()
    key = data["key"]
    # Check collision with code and existing admin types
    if key in _CODE_TYPE_MAP:
        raise ValueError(f"Key '{key}' already exists in code-defined types.")
    for t in types:
        if t.get("key") == key:
            raise ValueError(f"Admin type with key '{key}' already exists.")
    # Check collision with module types
    for _slug, mt in _get_module_types():
        if mt.get("key") == key:
            raise ValueError(f"Key '{key}' already used by a module type.")
    types.append(data)
    cfg.value = types
    cfg.save(update_fields=["value"])
    return data


def admin_update_type(key: str, patch: dict) -> dict:
    """Patch an existing admin type. Raises ValueError if not found."""
    cfg, types = _load_admin_config()
    for i, t in enumerate(types):
        if t.get("key") == key:
            updated = {**t, **patch, "key": key}  # key is immutable
            types[i] = updated
            cfg.value = types
            cfg.save(update_fields=["value"])
            return updated
    raise ValueError(f"Admin type '{key}' not found.")


def admin_delete_type(key: str) -> None:
    """Remove an admin type. Raises ValueError if not found."""
    cfg, types = _load_admin_config()
    new_types = [t for t in types if t.get("key") != key]
    if len(new_types) == len(types):
        raise ValueError(f"Admin type '{key}' not found.")
    cfg.value = new_types
    cfg.save(update_fields=["value"])
