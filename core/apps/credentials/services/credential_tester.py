"""Credential test/validate service — real connectivity checks per type.

Each tester returns (ok: bool, message: str).
If a type has no meaningful remote test, returns ok=False with an explicit
"not supported" message rather than a silent success.
"""
from __future__ import annotations

import requests

_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _test_openai_compatible(data: dict, type_key: str) -> tuple[bool, str]:
    """Test OpenAI-compatible API (openai, ollama) by calling GET /models."""
    api_key = data.get("api_key", "")
    base_url = (data.get("base_url") or "https://api.openai.com/v1").rstrip("/")

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(f"{base_url}/models", headers=headers, timeout=_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        return False, f"Connection error: {exc}"

    if resp.status_code == 401:
        return False, "Authentication failed: invalid API key"
    if resp.status_code == 403:
        return False, "Authentication failed: access forbidden"
    if not resp.ok:
        return False, f"API returned {resp.status_code}: {resp.text[:200]}"
    return True, "OK"


# ---------------------------------------------------------------------------
# Per-type testers
# ---------------------------------------------------------------------------

def test_telegram(data: dict) -> tuple[bool, str]:
    bot_token = data.get("bot_token", "").strip()
    if not bot_token:
        return False, "bot_token is missing"
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getMe",
            timeout=_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        return False, f"Connection error: {exc}"

    try:
        body = resp.json()
    except Exception:
        return False, f"Unexpected response (status {resp.status_code})"

    if body.get("ok") is True:
        username = body.get("result", {}).get("username", "")
        return True, f"OK — @{username}" if username else "OK"
    else:
        description = body.get("description", "Unknown error")
        return False, f"Telegram error: {description}"


def test_openai(data: dict) -> tuple[bool, str]:
    return _test_openai_compatible(data, "openai")


def test_ai_studio(data: dict) -> tuple[bool, str]:
    """Test Google AI Studio key by listing models."""
    api_key = data.get("api_key", "").strip()
    if not api_key:
        return False, "api_key is missing"
    try:
        resp = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"key": api_key},
            timeout=_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        return False, f"Connection error: {exc}"

    if resp.status_code == 400:
        return False, "Invalid API key format"
    if resp.status_code == 403:
        return False, "Authentication failed: API key rejected"
    if not resp.ok:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            msg = resp.text[:200]
        return False, f"AI Studio error: {msg}"
    return True, "OK"


def test_ollama(data: dict) -> tuple[bool, str]:
    return _test_openai_compatible(data, "ollama")


def test_google_oauth(data: dict, type_key: str) -> tuple[bool, str]:
    """Check that an OAuth2 Google credential has a non-expired access_token."""
    from datetime import datetime, timezone as dt_timezone, timedelta

    access_token = data.get("access_token", "").strip()
    if not access_token:
        return False, "Not connected — please authorize via OAuth"

    expires_at_str = data.get("expires_at", "")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=dt_timezone.utc)
            if expires_at <= datetime.now(dt_timezone.utc) + timedelta(seconds=60):
                refresh_token = data.get("refresh_token", "")
                if not refresh_token:
                    return False, "Token expired and no refresh_token — please re-authorize"
                # Has refresh token → token will be refreshed on actual use; report as ok
                return True, "Token expired but refresh_token present — will auto-refresh on use"
        except (ValueError, TypeError):
            pass

    # Verify token is actually accepted by Google tokeninfo endpoint
    try:
        resp = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": access_token},
            timeout=_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        return False, f"Connection error: {exc}"

    if resp.status_code == 400:
        return False, "Token invalid or expired — please re-authorize"
    if not resp.ok:
        return False, f"Token validation failed (status {resp.status_code})"

    account = data.get("account_email", "")
    return True, f"OK — {account}" if account else "OK"


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_TESTERS: dict[str, callable] = {
    "telegram": test_telegram,
    "openai": test_openai,
    "ai_studio": test_ai_studio,
    "ollama": test_ollama,
    "google_email": lambda d: test_google_oauth(d, "google_email"),
    "google_sheets": lambda d: test_google_oauth(d, "google_sheets"),
    "google_drive": lambda d: test_google_oauth(d, "google_drive"),
}


def test_credential(type_key: str, data: dict) -> dict:
    """Run the appropriate connectivity test for *type_key*.

    Returns {"ok": bool, "message": str}.
    Never raises — all exceptions are caught and returned as failures.
    """
    tester = _TESTERS.get(type_key)
    if tester is None:
        return {"ok": False, "message": f"Test not supported for type '{type_key}'"}

    try:
        ok, message = tester(data)
        return {"ok": ok, "message": message}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"Unexpected error: {exc}"}
