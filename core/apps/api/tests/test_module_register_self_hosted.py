"""Tests for POST /api/project/{id}/modules/register-self-hosted/"""

import pytest
from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel, PlanModel
from core.apps.api.models.module import ModuleModel, ProjectModuleModel
from core.apps.api.services.project import create_default_collections


@pytest.fixture(autouse=True)
def patch_docker_services():
    with (
        patch("core.apps.api.signals.project.remove_service"),
        patch("core.apps.api.signals.project.deploy_service") as mock_deploy,
        patch("core.apps.api.views.project.deploy_service") as mock_deploy_view,
        patch("core.apps.api.views.project.set_webhook"),
    ):
        magic = MagicMock()
        magic.metadata.name = "test-deployment-123"
        mock_deploy.return_value = magic
        mock_deploy_view.return_value = magic
        yield


@pytest.fixture
def test_plan(db):
    return PlanModel._create_fake()


@pytest.fixture
def project_with_client(db, test_plan):
    instance = ProjectModel._create_fake()
    create_default_collections(instance)
    instance.owner.balance = 1000000
    instance.owner.save()
    client = APIClient()
    client.force_authenticate(instance.owner)
    url = reverse("project-module-register-self-hosted", kwargs={"pk": instance.pk})
    return client, url, instance


VALID_MANIFEST_RESPONSE = {
    "result": {
        "module": "my-module",
        "nodes": [
            {
                "type": "my-module.Echo",
                "fields": [{"name": "message", "type": "text"}],
            }
        ],
    }
}

VALID_DOCS_RESPONSE = {"result": {"markdown": "# My Module"}}


def _mock_requests_post_side_effect(describe_resp=None, docs_resp=None):
    """Returns side_effect list: [describe, docs]."""
    d = MagicMock()
    d.json.return_value = describe_resp or VALID_MANIFEST_RESPONSE
    d.ok = True
    d.raise_for_status = MagicMock()

    doc = MagicMock()
    doc.json.return_value = docs_resp or VALID_DOCS_RESPONSE
    doc.ok = True
    doc.raise_for_status = MagicMock()

    return [d, doc]


@pytest.mark.django_db
class TestRegisterSelfHosted:
    @patch("core.apps.api.services.module_service.requests.post")
    def test_success_creates_module_and_project_module(self, mock_post, project_with_client):
        mock_post.side_effect = _mock_requests_post_side_effect()
        client, url, project = project_with_client

        resp = client.post(url, {"endpoint": "https://my-server.com/rpc"}, format="json")

        assert resp.status_code == 201, resp.data
        data = resp.json()
        assert data["status"] == "running"
        assert data["enabled"] is True
        assert data["module"]["source"]["mode"] == "endpoint"
        assert data["module"]["source"]["endpoint"] == "https://my-server.com/rpc"

        # DB'da yaratilganini tekshir
        assert ProjectModuleModel.objects.filter(project=project).exists()

    @patch("core.apps.api.services.module_service.requests.post")
    def test_name_used_as_module_name(self, mock_post, project_with_client):
        mock_post.side_effect = _mock_requests_post_side_effect()
        client, url, _ = project_with_client

        resp = client.post(url, {"endpoint": "https://my-server.com/rpc", "name": "Ajoyib Modul"}, format="json")

        assert resp.status_code == 201, resp.data
        assert resp.json()["module"]["name"] == "Ajoyib Modul"

    @pytest.mark.django_db
    def test_missing_endpoint_returns_400(self, project_with_client):
        client, url, _ = project_with_client
        resp = client.post(url, {}, format="json")
        assert resp.status_code == 400
        assert "endpoint" in resp.json()["detail"]

    @pytest.mark.django_db
    def test_invalid_url_returns_400(self, project_with_client):
        client, url, _ = project_with_client
        resp = client.post(url, {"endpoint": "not-a-url"}, format="json")
        assert resp.status_code == 400
        assert "URL" in resp.json()["detail"]

    @patch("core.apps.api.services.module_service.requests.post")
    def test_unreachable_endpoint_returns_400(self, mock_post, project_with_client):
        mock_post.side_effect = Exception("Connection refused")
        client, url, _ = project_with_client

        resp = client.post(url, {"endpoint": "https://unreachable.example.com/rpc"}, format="json")

        assert resp.status_code == 400
        assert "ulanmadi" in resp.json()["detail"]
        # Modul yaratilmagan bo'lishi kerak (cleanup)
        assert not ModuleModel.objects.filter(
            manifest_cache__contains='"endpoint": "https://unreachable.example.com/rpc"'
        ).exists()

    @pytest.mark.django_db
    def test_unauthenticated_returns_401(self, project_with_client, db):
        _, url, _ = project_with_client
        anon_client = APIClient()
        resp = anon_client.post(url, {"endpoint": "https://my-server.com/rpc"}, format="json")
        assert resp.status_code == 401

    @pytest.mark.django_db
    def test_other_user_cannot_access(self, project_with_client, test_plan, db):
        _, url, _ = project_with_client
        other = ProjectModel._create_fake()
        other_client = APIClient()
        other_client.force_authenticate(other.owner)
        resp = other_client.post(url, {"endpoint": "https://my-server.com/rpc"}, format="json")
        # Loyiha boshqa userni emas — 404 (owner check)
        assert resp.status_code == 404

    @patch("core.apps.api.services.module_service.requests.post")
    def test_same_endpoint_reuses_module(self, mock_post, project_with_client):
        """Bir xil endpoint ikkinchi marta qo'shilganda yangi ModuleModel yaratilmaydi."""
        mock_post.side_effect = (
            _mock_requests_post_side_effect()
            + _mock_requests_post_side_effect()
        )
        client, url, _ = project_with_client

        resp1 = client.post(url, {"endpoint": "https://my-server.com/rpc"}, format="json")
        assert resp1.status_code == 201

        resp2 = client.post(url, {"endpoint": "https://my-server.com/rpc"}, format="json")
        # Ikkinchi marta ham muvaffaqiyatli (yoki already-enabled 200)
        assert resp2.status_code in (200, 201)

        # Bitta ModuleModel bo'lishi kerak (duplicate emas)
        count = sum(
            1
            for m in ModuleModel.objects.all()
            if (m.manifest_cache or {}).get("_source", {}).get("endpoint") == "https://my-server.com/rpc"
        )
        assert count == 1

    @patch("core.apps.api.services.module_service.requests.post")
    def test_auth_token_saved(self, mock_post, project_with_client):
        mock_post.side_effect = _mock_requests_post_side_effect()
        client, url, _ = project_with_client

        resp = client.post(
            url,
            {"endpoint": "https://my-server.com/rpc", "auth_token": "supersecret"},
            format="json",
        )
        assert resp.status_code == 201
        module = ModuleModel.objects.get(
            manifest_cache__contains='"mode": "endpoint"',
        )
        # Endpoint'ı tekshirish uchun filter
        found = None
        for m in ModuleModel.objects.all():
            src = (m.manifest_cache or {}).get("_source", {})
            if src.get("endpoint") == "https://my-server.com/rpc":
                found = m
                break
        assert found is not None
        assert found.auth_token == "supersecret"
