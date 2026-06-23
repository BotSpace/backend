"""Tests for POST /api/modules/register-github/ (admin-only) and _github_raw_yaml_url helper."""

import pytest
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.views.module import _github_raw_yaml_url

User = get_user_model()


# ---------------------------------------------------------------------------
# Pure-unit: _github_raw_yaml_url
# ---------------------------------------------------------------------------

class TestGithubRawYamlUrl:
    def test_plain_url(self):
        raw, canonical = _github_raw_yaml_url("https://github.com/owner/my-module")
        assert raw == "https://raw.githubusercontent.com/owner/my-module/HEAD/module.yaml"
        assert canonical == "https://github.com/owner/my-module"

    def test_dot_git_suffix_stripped(self):
        raw, canonical = _github_raw_yaml_url("https://github.com/owner/my-module.git")
        assert raw == "https://raw.githubusercontent.com/owner/my-module/HEAD/module.yaml"
        assert canonical == "https://github.com/owner/my-module"

    def test_trailing_slash_stripped(self):
        raw, canonical = _github_raw_yaml_url("https://github.com/owner/my-module/")
        assert canonical == "https://github.com/owner/my-module"
        assert "HEAD/module.yaml" in raw

    def test_both_suffix_and_trailing_slash(self):
        raw, _ = _github_raw_yaml_url("https://github.com/owner/my-module.git/")
        assert "HEAD/module.yaml" in raw

    def test_non_github_url_raises(self):
        with pytest.raises(ValueError, match="GitHub"):
            _github_raw_yaml_url("https://gitlab.com/owner/repo")

    def test_missing_repo_raises(self):
        with pytest.raises(ValueError):
            _github_raw_yaml_url("https://github.com/owner")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _github_raw_yaml_url("")


# ---------------------------------------------------------------------------
# Integration: POST /api/modules/register-github/ (admin-only)
# ---------------------------------------------------------------------------

VALID_MODULE_YAML = """
apiVersion: botmother.module/v1
module:
  id: test-gh-module
  name: Test GitHub Module
source:
  github: https://github.com/test-owner/test-repo
runtime:
  port: 8100
  dockerfile: Dockerfile
"""


@pytest.fixture
def admin_client(db):
    user = User.objects.create_superuser(phone="+998901234567", password="pass", is_staff=True)
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def regular_client(db):
    user = User.objects.create_user(phone="+998907654321", password="pass")
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def register_github_url():
    return reverse("modules-register-github")


@pytest.mark.django_db
class TestAdminRegisterGithub:
    @patch("core.apps.api.services.kubernetes_service.create_module_build_job", return_value="job-abc123")
    @patch("core.apps.api.views.module._fetch_github_module_yaml", return_value=(VALID_MODULE_YAML, "https://github.com/test-owner/test-repo"))
    def test_success_returns_module_and_build_job(self, mock_fetch, mock_build, admin_client, register_github_url):
        resp = admin_client.post(register_github_url, {"repo_url": "https://github.com/test-owner/test-repo"}, format="json")

        assert resp.status_code == 201, resp.data
        data = resp.json()
        assert data["ok"] is True
        assert data["mode"] == "github"
        assert data["module"]["slug"] == "test-gh-module"
        assert data["build_job"] == "job-abc123"

    def test_missing_repo_url_returns_400(self, admin_client, register_github_url):
        resp = admin_client.post(register_github_url, {}, format="json")
        assert resp.status_code == 400
        assert "repo_url" in resp.json()["detail"]

    def test_non_github_url_returns_400(self, admin_client, register_github_url):
        resp = admin_client.post(register_github_url, {"repo_url": "https://gitlab.com/owner/repo"}, format="json")
        assert resp.status_code == 400
        assert "GitHub" in resp.json()["detail"]

    @patch("core.apps.api.views.module._fetch_github_module_yaml", side_effect=ValueError("repo ichida module.yaml topilmadi"))
    def test_yaml_not_found_returns_400(self, mock_fetch, admin_client, register_github_url):
        resp = admin_client.post(register_github_url, {"repo_url": "https://github.com/owner/no-yaml-repo"}, format="json")
        assert resp.status_code == 400
        assert "module.yaml" in resp.json()["detail"]

    def test_regular_user_forbidden(self, regular_client, register_github_url):
        resp = regular_client.post(register_github_url, {"repo_url": "https://github.com/owner/repo"}, format="json")
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, register_github_url):
        anon = APIClient()
        resp = anon.post(register_github_url, {"repo_url": "https://github.com/owner/repo"}, format="json")
        assert resp.status_code == 401

    @patch("core.apps.api.services.kubernetes_service.create_module_build_job", return_value="job-idempotent")
    @patch("core.apps.api.views.module._fetch_github_module_yaml", return_value=(VALID_MODULE_YAML, "https://github.com/test-owner/test-repo"))
    def test_idempotent_updates_existing_module(self, mock_fetch, mock_build, admin_client, register_github_url):
        """Bir xil repo ikkinchi marta qo'shilganda yangi ModuleModel yaratilmaydi — mavjudi yangilanadi."""
        from core.apps.api.models.module import ModuleModel

        resp1 = admin_client.post(register_github_url, {"repo_url": "https://github.com/test-owner/test-repo"}, format="json")
        assert resp1.status_code == 201

        resp2 = admin_client.post(register_github_url, {"repo_url": "https://github.com/test-owner/test-repo"}, format="json")
        assert resp2.status_code == 201

        assert ModuleModel.objects.filter(slug="test-gh-module").count() == 1
