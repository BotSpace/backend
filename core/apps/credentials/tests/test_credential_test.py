"""Tests for credential test/validate service (services/credential_tester.py).

All tests are pure-unit — no DB, no network (requests mocked).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.apps.credentials.services.credential_tester import test_credential as run_test


_PATCH = "core.apps.credentials.services.credential_tester.requests.get"


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

class TestTelegramCredentialTest:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {"username": "mybot"}}
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("telegram", {"bot_token": "123:ABC"})
        assert result["ok"] is True
        assert "@mybot" in result["message"]

    def test_invalid_token(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False, "description": "Unauthorized"}
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("telegram", {"bot_token": "badtoken"})
        assert result["ok"] is False
        assert "Unauthorized" in result["message"]

    def test_missing_token(self):
        result = run_test("telegram", {})
        assert result["ok"] is False
        assert "missing" in result["message"].lower()

    def test_network_error(self):
        import requests as real_requests
        with patch(_PATCH, side_effect=real_requests.exceptions.ConnectionError("timeout")):
            result = run_test("telegram", {"bot_token": "123:ABC"})
        assert result["ok"] is False
        assert "Connection error" in result["message"]


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class TestOpenAICredentialTest:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("openai", {"api_key": "sk-real", "base_url": "https://api.openai.com/v1"})
        assert result["ok"] is True

    def test_invalid_key(self):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 401
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("openai", {"api_key": "sk-bad"})
        assert result["ok"] is False
        assert "invalid api key" in result["message"].lower()

    def test_forbidden(self):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 403
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("openai", {"api_key": "sk-bad"})
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# Google AI Studio
# ---------------------------------------------------------------------------

class TestAIStudioCredentialTest:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("ai_studio", {"api_key": "AIza_valid"})
        assert result["ok"] is True

    def test_rejected_key(self):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 403
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("ai_studio", {"api_key": "AIza_bad"})
        assert result["ok"] is False

    def test_missing_key(self):
        result = run_test("ai_studio", {})
        assert result["ok"] is False
        assert "missing" in result["message"].lower()


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

class TestOllamaCredentialTest:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("ollama", {"base_url": "http://localhost:11434/v1"})
        assert result["ok"] is True

    def test_unreachable(self):
        import requests as real_requests
        with patch(_PATCH, side_effect=real_requests.exceptions.ConnectionError("refused")):
            result = run_test("ollama", {"base_url": "http://localhost:11434/v1"})
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# Google OAuth types
# ---------------------------------------------------------------------------

class TestGoogleOAuthCredentialTest:
    def _valid_token_data(self):
        from datetime import datetime, timezone as dt_timezone, timedelta
        future = (datetime.now(dt_timezone.utc) + timedelta(hours=1)).isoformat()
        return {
            "access_token": "ya29.valid",
            "refresh_token": "1//refresh",
            "expires_at": future,
            "account_email": "user@example.com",
        }

    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("google_sheets", self._valid_token_data())
        assert result["ok"] is True
        assert "user@example.com" in result["message"]

    def test_no_access_token(self):
        result = run_test("google_email", {})
        assert result["ok"] is False
        assert "authorize" in result["message"].lower()

    def test_invalid_token(self):
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 400
        with patch(_PATCH, return_value=mock_resp):
            result = run_test("google_drive", self._valid_token_data())
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# Unsupported / unknown type
# ---------------------------------------------------------------------------

def test_unsupported_type_returns_failure():
    result = run_test("bearer", {"token": "xyz"})
    assert result["ok"] is False
    assert "not supported" in result["message"].lower()


def test_unknown_type_returns_failure():
    result = run_test("nonexistent_type", {})
    assert result["ok"] is False
    assert "not supported" in result["message"].lower()
