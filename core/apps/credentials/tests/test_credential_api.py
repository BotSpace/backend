"""Owner-scoped CRUD, masking, filtering tests for Credentials API v2."""
import pytest
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel
from core.apps.credentials.models import Credential
from core.apps.credentials.services import crypto


def _make_credential(owner, type_key="bearer", name="Test cred", data=None):
    if data is None:
        data = {"token": "supersecret1234"}
    return Credential.objects.create(
        owner=owner,
        type_key=type_key,
        name=name,
        data_encrypted=crypto.encrypt(data),
    )


@pytest.fixture
def auth_client(db):
    project = ProjectModel._create_fake()
    client = APIClient()
    client.force_authenticate(project.owner)
    return client, project.owner


@pytest.mark.django_db
def test_create_credential(auth_client):
    client, owner = auth_client
    resp = client.post(
        "/api/v1/credentials/",
        {"type_key": "bearer", "name": "My token", "data": {"token": "supersecret123"}},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My token"
    assert data["type_key"] == "bearer"
    assert data["mode"] == "bearer"
    # secret field must be masked in response
    assert data["data"]["token"] != "supersecret123"
    assert data["data"]["token"].startswith("••••")


@pytest.mark.django_db
def test_create_invalid_type_key(auth_client):
    client, owner = auth_client
    resp = client.post(
        "/api/v1/credentials/",
        {"type_key": "nonexistent_type", "name": "Bad", "data": {}},
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_list_credentials(auth_client):
    client, owner = auth_client
    _make_credential(owner, name="Token A", data={"token": "abc12345"})
    resp = client.get("/api/v1/credentials/")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["name"] == "Token A"
    # masked: last 4 of "abc12345" = "2345"
    assert results[0]["data"]["token"] == "••••" + "2345"


@pytest.mark.django_db
def test_list_filter_by_type_key(auth_client):
    client, owner = auth_client
    _make_credential(owner, type_key="bearer", name="Bear", data={"token": "abc123456"})
    _make_credential(
        owner,
        type_key="api_key",
        name="Api",
        data={"token": "xyz123456", "param_name": "X-API-Key", "placement": "header"},
    )
    resp = client.get("/api/v1/credentials/?type_key=bearer")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["name"] == "Bear"


@pytest.mark.django_db
def test_retrieve_credential(auth_client):
    client, owner = auth_client
    cred = _make_credential(owner)
    resp = client.get(f"/api/v1/credentials/{cred.id}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == cred.id


@pytest.mark.django_db
def test_patch_keeps_secret_if_omitted(auth_client):
    client, owner = auth_client
    cred = _make_credential(owner, name="Old name", data={"token": "original_secret_val"})
    resp = client.patch(
        f"/api/v1/credentials/{cred.id}/",
        {"name": "New name", "data": {"token": ""}},
        format="json",
    )
    assert resp.status_code == 200
    cred.refresh_from_db()
    assert cred.name == "New name"
    decrypted = crypto.decrypt(cred.data_encrypted)
    assert decrypted["token"] == "original_secret_val"  # not cleared


@pytest.mark.django_db
def test_patch_updates_secret_when_provided(auth_client):
    client, owner = auth_client
    cred = _make_credential(owner, name="Name", data={"token": "old"})
    resp = client.patch(
        f"/api/v1/credentials/{cred.id}/",
        {"data": {"token": "new_token_value"}},
        format="json",
    )
    assert resp.status_code == 200
    cred.refresh_from_db()
    assert crypto.decrypt(cred.data_encrypted)["token"] == "new_token_value"


@pytest.mark.django_db
def test_soft_delete(auth_client):
    client, owner = auth_client
    cred = _make_credential(owner, name="To delete")
    resp = client.delete(f"/api/v1/credentials/{cred.id}/")
    assert resp.status_code == 204
    cred.refresh_from_db()
    assert cred.deleted_at is not None
    # Should not appear in list
    list_resp = client.get("/api/v1/credentials/")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 0


@pytest.mark.django_db
def test_owner_scoping():
    """User A cannot access User B's credentials."""
    project_a = ProjectModel._create_fake()
    project_b = ProjectModel._create_fake()

    cred_b = _make_credential(project_b.owner, name="Secret B")

    client_a = APIClient()
    client_a.force_authenticate(project_a.owner)

    # Direct retrieve — 404 because owner filter hides it
    resp = client_a.get(f"/api/v1/credentials/{cred_b.id}/")
    assert resp.status_code == 404

    # List — empty
    list_resp = client_a.get("/api/v1/credentials/")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 0


@pytest.mark.django_db
def test_test_stub(auth_client):
    client, owner = auth_client
    cred = _make_credential(owner)
    resp = client.post(f"/api/v1/credentials/{cred.id}/test/")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.django_db
def test_types_list(auth_client):
    client, _ = auth_client
    resp = client.get("/api/v1/credentials/types/")
    assert resp.status_code == 200
    keys = [t["key"] for t in resp.json()]
    assert "bearer" in keys
    assert "api_key" in keys
    assert "basic_auth" in keys
    assert "header_auth" in keys
    assert "telegram" in keys
    assert "google_email" in keys
    assert "google_sheets" in keys
    assert "google_drive" in keys
