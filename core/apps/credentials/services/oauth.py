"""OAuth2 helper services.

- State token signing/verification (TimestampSigner, ~10 min TTL)
- Token exchange + userinfo fetch
- Token refresh (used by internal endpoint)
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone as dt_timezone
from typing import Any

import requests as http_requests
from django.core import signing

# State token max age in seconds (10 minutes)
STATE_MAX_AGE = 600
CALLBACK_URL = "https://api.botspace.uz/api/v1/credentials/oauth/{provider}/callback/"


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def make_state(user_id: int, type_key: str) -> str:
    """Sign and return a short-lived state token embedding user_id + type_key + nonce."""
    nonce = secrets.token_hex(8)
    payload = f"{user_id}:{type_key}:{nonce}"
    signer = signing.TimestampSigner()
    return signer.sign(payload)


def verify_state(state: str) -> dict[str, Any]:
    """Verify state token and return {user_id, type_key}.

    Raises signing.BadSignature / signing.SignatureExpired on failure.
    """
    signer = signing.TimestampSigner()
    value = signer.unsign(state, max_age=STATE_MAX_AGE)
    parts = value.split(":", 2)
    if len(parts) < 3:
        raise signing.BadSignature("Malformed state payload")
    user_id, type_key, _nonce = parts
    return {"user_id": int(user_id), "type_key": type_key}


# ---------------------------------------------------------------------------
# Token exchange
# ---------------------------------------------------------------------------

def exchange_code(provider_cfg: dict, provider: str, code: str) -> dict:
    """Exchange authorization code for tokens.  Returns raw token response dict."""
    redirect_uri = CALLBACK_URL.format(provider=provider)
    resp = http_requests.post(
        provider_cfg["token_url"],
        data={
            "code": code,
            "client_id": provider_cfg["client_id"],
            "client_secret": provider_cfg["client_secret"],
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_userinfo(provider_cfg: dict, access_token: str) -> dict:
    """Fetch user info from provider's userinfo endpoint."""
    resp = http_requests.get(
        provider_cfg["userinfo_url"],
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.ok:
        return resp.json()
    return {}


def build_token_data(token_resp: dict, userinfo: dict | None = None) -> dict:
    """Normalise a raw token response into the data dict we store."""
    import_datetime = datetime.now(dt_timezone.utc)
    expires_in = token_resp.get("expires_in", 3600)
    from datetime import timedelta
    expires_at = (import_datetime + timedelta(seconds=int(expires_in))).isoformat()

    data: dict = {
        "access_token": token_resp.get("access_token", ""),
        "refresh_token": token_resp.get("refresh_token", ""),
        "expires_at": expires_at,
        "scope": token_resp.get("scope", ""),
        "token_type": token_resp.get("token_type", "Bearer"),
        "account_email": "",
    }
    if userinfo:
        data["account_email"] = userinfo.get("email", "")
    return data


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

def get_valid_access_token(credential) -> str:
    """Return a valid access_token for an oauth2 credential.

    If expired (or expiring within 60 s), refresh using refresh_token,
    update encrypted data in DB, and return fresh access_token.
    """
    from core.apps.credentials.oauth_providers import get_provider
    from core.apps.credentials.registry import get_type
    from core.apps.credentials.services import crypto

    type_info = get_type(credential.type_key)
    if type_info is None or type_info.get("mode") != "oauth2":
        raise ValueError(f"Credential {credential.id} is not oauth2 type")

    provider_name = type_info.get("provider", "")
    provider_cfg = get_provider(provider_name)
    if provider_cfg is None:
        raise ValueError(f"Unknown OAuth provider: {provider_name}")

    try:
        data = crypto.decrypt(credential.data_encrypted)
    except Exception as exc:
        raise ValueError(f"Cannot decrypt credential {credential.id}: {exc}") from exc

    access_token = data.get("access_token", "")
    expires_at_str = data.get("expires_at", "")
    refresh_token = data.get("refresh_token", "")

    # Check if refresh needed (expired or expiring within 60 s)
    needs_refresh = True
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt_timezone.utc)
            now = datetime.now(dt_timezone.utc)
            from datetime import timedelta
            needs_refresh = expires_at <= now + timedelta(seconds=60)
        except (ValueError, TypeError):
            needs_refresh = True

    if not needs_refresh and access_token:
        return access_token

    if not refresh_token:
        raise ValueError(f"No refresh_token for credential {credential.id}; user must re-authorize")

    # Refresh
    resp = http_requests.post(
        provider_cfg["token_url"],
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": provider_cfg["client_id"],
            "client_secret": provider_cfg["client_secret"],
        },
        timeout=15,
    )
    resp.raise_for_status()
    token_resp = resp.json()

    # Merge new tokens into existing data (preserve account_email, keep refresh_token if not returned)
    from datetime import timedelta
    expires_in = token_resp.get("expires_in", 3600)
    new_expires_at = (datetime.now(dt_timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

    data["access_token"] = token_resp["access_token"]
    data["expires_at"] = new_expires_at
    if token_resp.get("refresh_token"):
        data["refresh_token"] = token_resp["refresh_token"]
    data["token_type"] = token_resp.get("token_type", data.get("token_type", "Bearer"))

    credential.data_encrypted = crypto.encrypt(data)
    credential.save(update_fields=["data_encrypted", "updated_at"])

    return data["access_token"]
