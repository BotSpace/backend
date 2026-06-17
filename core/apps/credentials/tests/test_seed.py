"""Registry list tests — v2 (no DB CredentialType model)."""
import pytest

from core.apps.credentials.registry import get_type, list_types

EXPECTED_KEYS = ["api_key", "bearer", "header_auth", "basic_auth", "telegram", "google"]


def test_all_builtin_types_present():
    keys = [t["key"] for t in list_types()]
    for key in EXPECTED_KEYS:
        assert key in keys, f"Registry key={key!r} not found"


def test_api_key_has_required_fields():
    info = get_type("api_key")
    assert info is not None
    field_names = [f["name"] for f in info["fields"]]
    assert "token" in field_names
    assert "param_name" in field_names
    assert "placement" in field_names


def test_bearer_mode():
    info = get_type("bearer")
    assert info is not None
    assert info["mode"] == "bearer"


def test_basic_auth_fields():
    info = get_type("basic_auth")
    assert info is not None
    field_names = [f["name"] for f in info["fields"]]
    assert "username" in field_names
    assert "password" in field_names


def test_get_type_unknown_returns_none():
    assert get_type("nonexistent_xyz") is None


def test_all_types_have_required_keys():
    for t in list_types():
        assert "key" in t
        assert "label" in t
        assert "mode" in t
        assert "fields" in t
        assert isinstance(t["fields"], list)


def test_secret_fields_marked():
    """Bearer token field must be marked secret."""
    info = get_type("bearer")
    token_field = next(f for f in info["fields"] if f["name"] == "token")
    assert token_field.get("secret") is True
