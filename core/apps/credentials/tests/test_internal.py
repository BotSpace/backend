"""Internal engine-facing endpoint tests."""
import pytest
from model_bakery import baker
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel
from core.apps.credentials.models import Credential, CredentialType
from core.apps.credentials.services import crypto


INTERNAL_TOKEN = "test-internal-secret"
INTERNAL_URL = "/api/v1/internal/credentials/{pk}/"


@pytest.fixture(autouse=True)
def set_internal_token(settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN


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
def credential(db, bearer_type):
    project = ProjectModel._create_fake()
    return Credential.objects.create(
        project=project,
        owner=project.owner,
        type=bearer_type,
        name="Engine cred",
        data_encrypted=crypto.encrypt({"token": "plaintext_secret"}),
    )


@pytest.mark.django_db
def test_internal_200_with_valid_token(credential):
    client = APIClient()
    url = INTERNAL_URL.format(pk=credential.id)
    resp = client.get(url, HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == credential.id
    assert data["name"] == "Engine cred"
    assert data["project_id"] == credential.project_id
    assert data["type"]["key"] == "bearer"
    assert data["type"]["mode"] == "bearer"
    # Decrypted — plaintext
    assert data["data"]["token"] == "plaintext_secret"


@pytest.mark.django_db
def test_internal_401_without_token(credential):
    client = APIClient()
    url = INTERNAL_URL.format(pk=credential.id)
    resp = client.get(url)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_internal_401_wrong_token(credential):
    client = APIClient()
    url = INTERNAL_URL.format(pk=credential.id)
    resp = client.get(url, HTTP_X_INTERNAL_TOKEN="wrong-token")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_internal_404_missing(db):
    client = APIClient()
    url = INTERNAL_URL.format(pk=99999)
    resp = client.get(url, HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_internal_404_soft_deleted(credential):
    from django.utils import timezone
    credential.deleted_at = timezone.now()
    credential.save(update_fields=["deleted_at"])

    client = APIClient()
    url = INTERNAL_URL.format(pk=credential.id)
    resp = client.get(url, HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN)
    assert resp.status_code == 404
