"""Check that built-in CredentialTypes are seeded."""
import pytest

from core.apps.credentials.models import CredentialType

EXPECTED_KEYS = ["api_key", "bearer", "header_auth", "basic_auth"]


@pytest.mark.django_db
def test_all_builtin_types_present():
    for key in EXPECTED_KEYS:
        ctype = CredentialType.objects.filter(key=key).first()
        assert ctype is not None, f"CredentialType key={key!r} not found"
        assert ctype.system is True
        assert ctype.owner is None


@pytest.mark.django_db
def test_api_key_has_required_fields():
    ctype = CredentialType.objects.get(key="api_key")
    field_names = [f["name"] for f in ctype.fields]
    assert "token" in field_names
    assert "param_name" in field_names
    assert "placement" in field_names


@pytest.mark.django_db
def test_bearer_mode():
    ctype = CredentialType.objects.get(key="bearer")
    assert ctype.mode == "bearer"


@pytest.mark.django_db
def test_basic_auth_fields():
    ctype = CredentialType.objects.get(key="basic_auth")
    field_names = [f["name"] for f in ctype.fields]
    assert "username" in field_names
    assert "password" in field_names
