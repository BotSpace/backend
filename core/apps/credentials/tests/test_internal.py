"""Internal engine-facing endpoint tests — v2 shape."""
import pytest
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel
from core.apps.credentials.models import Credential
from core.apps.credentials.services import crypto


INTERNAL_TOKEN = "test-internal-secret"
INTERNAL_URL = "/api/v1/internal/credentials/{pk}/"


@pytest.fixture(autouse=True)
def set_internal_token(settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN


def _make_credential(owner, type_key="bearer", name="Engine cred", data=None):
    if data is None:
        data = {"token": "plaintext_secret"}
    return Credential.objects.create(
        owner=owner,
        type_key=type_key,
        name=name,
        data_encrypted=crypto.encrypt(data),
    )


@pytest.fixture
def project_and_cred(db):
    project = ProjectModel._create_fake()
    cred = _make_credential(project.owner)
    return project, cred


@pytest.mark.django_db
def test_internal_200_with_valid_token(project_and_cred):
    project, credential = project_and_cred
    client = APIClient()
    url = INTERNAL_URL.format(pk=credential.id)
    resp = client.get(url, HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN, HTTP_X_PROJECT_ID=str(project.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == credential.id
    assert data["name"] == "Engine cred"
    assert data["type_key"] == "bearer"
    assert data["mode"] == "bearer"
    # Decrypted — plaintext
    assert data["data"]["token"] == "plaintext_secret"
    # v1 fields must NOT be present
    assert "project_id" not in data
    assert "type" not in data


@pytest.mark.django_db
def test_internal_200_without_project_id(project_and_cred):
    """X-Project-Id is optional — if not sent, no owner guard is applied."""
    project, credential = project_and_cred
    client = APIClient()
    url = INTERNAL_URL.format(pk=credential.id)
    resp = client.get(url, HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_internal_403_cross_tenant(db):
    """Owner mismatch: project belongs to user_b, credential belongs to user_a."""
    project_a = ProjectModel._create_fake()
    project_b = ProjectModel._create_fake()
    cred_a = _make_credential(project_a.owner, name="Cred A")

    client = APIClient()
    url = INTERNAL_URL.format(pk=cred_a.id)
    # Requesting with project_b's id — owner mismatch
    resp = client.get(url, HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN, HTTP_X_PROJECT_ID=str(project_b.id))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_internal_401_without_token(project_and_cred):
    project, credential = project_and_cred
    client = APIClient()
    url = INTERNAL_URL.format(pk=credential.id)
    resp = client.get(url)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_internal_401_wrong_token(project_and_cred):
    project, credential = project_and_cred
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
def test_internal_404_soft_deleted(project_and_cred):
    project, credential = project_and_cred
    from django.utils import timezone
    credential.deleted_at = timezone.now()
    credential.save(update_fields=["deleted_at"])

    client = APIClient()
    url = INTERNAL_URL.format(pk=credential.id)
    resp = client.get(url, HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN)
    assert resp.status_code == 404
