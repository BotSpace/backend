"""OAuth2 provider registry.

Provider config (client_id/secret) is resolved from dynamic admin config
(OptionsModel via get_config) with env var fallback.
"""
from __future__ import annotations

import os

from django.conf import settings


def _get_google_client_id() -> str:
    from core.apps.shared.utils.settings import get_config
    val = get_config("oauth_google", "client_id")
    if val:
        return val[0] if isinstance(val, (list, tuple)) else val
    return os.environ.get("GOOGLE_OAUTH_CLIENT_ID", getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", ""))


def _get_google_client_secret() -> str:
    from core.apps.shared.utils.settings import get_config
    val = get_config("oauth_google", "client_secret")
    if val:
        return val[0] if isinstance(val, (list, tuple)) else val
    return os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", ""))


OAUTH_PROVIDERS: dict[str, dict] = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        # client_id / client_secret are resolved lazily via callables so admin config changes
        # take effect without restart.
        "_client_id_fn": _get_google_client_id,
        "_client_secret_fn": _get_google_client_secret,
        "extra_authorize_params": {
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
        },
    },
}


def get_provider(name: str) -> dict | None:
    """Return provider config (with resolved client_id/client_secret) or None."""
    cfg = OAUTH_PROVIDERS.get(name)
    if cfg is None:
        return None
    # Resolve callables into real values (fresh on every call)
    result = dict(cfg)
    result["client_id"] = cfg["_client_id_fn"]()
    result["client_secret"] = cfg["_client_secret_fn"]()
    result.pop("_client_id_fn", None)
    result.pop("_client_secret_fn", None)
    return result
