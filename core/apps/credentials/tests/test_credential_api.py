"""CRUD, masking, project-scoping tests for credentials API."""
import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel
from core.apps.credentials.models import Credential, CredentialType
from core.apps.credentials.services import crypto


@pytest.fixture
def bearer_type(db):
    ctype, _ = CredentialType.objects.get_or_create(
        key="bearer",
        defaults={
            "label": "Bearer Token",
            "icon": "shield",
            "mode": "bearer",
            "system": True,
            "fields": [{"name": "token", "label": "Token", "type": "password", "secret": True, "required": True}],
        },
    )
    return ctype


@pytest.fixture
def project_client(db):
    project = ProjectModel._create_fake()
    client = APIClient()
    client.force_authenticate(project.owner)
    return client, project


@pytest.mark.django_db
def test_create_credential(project_client, bearer_type):
    client, project = project_client
    url = f"/api/v1/credentials/projects/{project.id}/credentials/"
    resp = client.post(url, {"name": "My token", "type_id": bearer_type.id, "data": {"token": "supersecret123"}}, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My token"
    # secret field must be masked in response
    assert data["data"]["token"] != "supersecret123"
    assert data["data"]["token"].startswith("••••")


@pytest.mark.django_db
def test_list_credentials(project_client, bearer_type):
    client, project = project_client
    Credential.objects.create(
        project=project,
        owner=project.owner,
        type=bearer_type,
        name="Token A",
        data_encrypted=crypto.encrypt({"token": "abc12345"}),
    )
    url = f"/api/v1/credentials/projects/{project.id}/credentials/"
    resp = client.get(url)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["name"] == "Token A"
    # masked
    assert results[0]["data"]["token"] == "••••" + "2345"


@pytest.mark.django_db
def test_patch_keeps_secret_if_omitted(project_client, bearer_type):
    client, project = project_client
    cred = Credential.objects.create(
        project=project,
        owner=project.owner,
        type=bearer_type,
        name="Old name",
        data_encrypted=crypto.encrypt({"token": "original_secret"}),
    )
    url = f"/api/v1/credentials/projects/{project.id}/credentials/{cred.id}/"
    resp = client.patch(url, {"name": "New name", "data": {"token": ""}}, format="json")
    assert resp.status_code == 200
    cred.refresh_from_db()
    assert cred.name == "New name"
    decrypted = crypto.decrypt(cred.data_encrypted)
    assert decrypted["token"] == "original_secret"  # not cleared


@pytest.mark.django_db
def test_patch_updates_secret_when_provided(project_client, bearer_type):
    client, project = project_client
    cred = Credential.objects.create(
        project=project,
        owner=project.owner,
        type=bearer_type,
        name="Name",
        data_encrypted=crypto.encrypt({"token": "old"}),
    )
    url = f"/api/v1/credentials/projects/{project.id}/credentials/{cred.id}/"
    resp = client.patch(url, {"data": {"token": "new_token_value"}}, format="json")
    assert resp.status_code == 200
    cred.refresh_from_db()
    assert crypto.decrypt(cred.data_encrypted)["token"] == "new_token_value"


@pytest.mark.django_db
def test_soft_delete(project_client, bearer_type):
    client, project = project_client
    cred = Credential.objects.create(
        project=project,
        owner=project.owner,
        type=bearer_type,
        name="To delete",
        data_encrypted=crypto.encrypt({"token": "x"}),
    )
    url = f"/api/v1/credentials/projects/{project.id}/credentials/{cred.id}/"
    resp = client.delete(url)
    assert resp.status_code == 204
    cred.refresh_from_db()
    assert cred.deleted_at is not None
    # Should not appear in list
    list_resp = client.get(f"/api/v1/credentials/projects/{project.id}/credentials/")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 0


@pytest.mark.django_db
def test_project_scoping(bearer_type):
    """User A cannot access User B's credentials."""
    project_a = ProjectModel._create_fake()
    project_b = ProjectModel._create_fake()

    cred = Credential.objects.create(
        project=project_b,
        owner=project_b.owner,
        type=bearer_type,
        name="Secret B",
        data_encrypted=crypto.encrypt({"token": "secretB"}),
    )

    client_a = APIClient()
    client_a.force_authenticate(project_a.owner)

    # Trying to access project_b's credentials with project_a's auth
    url = f"/api/v1/credentials/projects/{project_b.id}/credentials/"
    resp = client_a.get(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_filter_by_type(project_client, bearer_type):
    client, project = project_client
    api_type, _ = CredentialType.objects.get_or_create(
        key="api_key",
        defaults={
            "label": "API Key",
            "icon": "key",
            "mode": "apikey",
            "system": True,
            "fields": [
                {"name": "token", "label": "Token", "type": "password", "secret": True, "required": True},
                {"name": "param_name", "label": "Param", "type": "text", "required": True, "default": "X-API-Key"},
                {
                    "name": "placement", "label": "Placement", "type": "select", "required": True,
                    "default": "header", "options": [{"value": "header", "label": "Header"}],
                },
            ],
        },
    )
    Credential.objects.create(
        project=project, owner=project.owner, type=bearer_type, name="Bear",
        data_encrypted=crypto.encrypt({"token": "abc123456"}),
    )
    Credential.objects.create(
        project=project, owner=project.owner, type=api_type, name="Api",
        data_encrypted=crypto.encrypt({"token": "xyz123456", "param_name": "X-API-Key", "placement": "header"}),
    )
    url = f"/api/v1/credentials/projects/{project.id}/credentials/?type=bearer"
    resp = client.get(url)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["name"] == "Bear"


@pytest.mark.django_db
def test_test_stub(project_client, bearer_type):
    client, project = project_client
    cred = Credential.objects.create(
        project=project, owner=project.owner, type=bearer_type, name="T",
        data_encrypted=crypto.encrypt({"token": "x"}),
    )
    url = f"/api/v1/credentials/projects/{project.id}/credentials/{cred.id}/test/"
    resp = client.post(url)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
