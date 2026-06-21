import pytest
from unittest.mock import MagicMock, patch

from core.apps.api.services.module_service import (
    ALLOWED_FIELD_TYPES,
    ManifestValidationError,
    fetch_manifest,
    get_project_module_manifests,
    get_project_modules_for_engine,
)


@pytest.fixture
def module():
    m = MagicMock()
    m.slug = "demo"
    m.name = "Demo Module"
    m.auth_token = "secret"
    m.manifest_cache = None
    m.manifest_fetched_at = None
    return m


@pytest.fixture
def project_module(module):
    pm = MagicMock()
    pm.module = module
    pm.endpoint = "http://module-demo-1:8100/rpc"
    pm.enabled = True
    return pm


class TestFetchManifest:
    @patch("core.apps.api.services.module_service.ProjectModuleModel")
    @patch("core.apps.api.services.module_service.requests.post")
    def test_valid_manifest(self, mock_post, mock_pm_model, module, project_module):
        mock_pm_model.objects.filter.return_value.first.return_value = project_module

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "module": "demo",
                "nodes": [
                    {
                        "type": "demo.Echo",
                        "fields": [
                            {"name": "message", "type": "text"},
                            {"name": "count", "type": "number"},
                        ],
                    }
                ],
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = fetch_manifest(module)

        assert result["module"] == "demo"
        assert len(result["nodes"]) == 1
        module.save.assert_called_once()

    @patch("core.apps.api.services.module_service.ProjectModuleModel")
    @patch("core.apps.api.services.module_service.requests.post")
    def test_unknown_field_type_raises(self, mock_post, mock_pm_model, module, project_module):
        mock_pm_model.objects.filter.return_value.first.return_value = project_module
        mock_pm_model.objects.filter.return_value.update = MagicMock()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "module": "demo",
                "nodes": [
                    {
                        "type": "demo.Echo",
                        "fields": [
                            {"name": "cfg", "type": "magic_unknown_type"},
                        ],
                    }
                ],
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with pytest.raises(ManifestValidationError) as exc_info:
            fetch_manifest(module)

        assert "magic_unknown_type" in str(exc_info.value)

    @patch("core.apps.api.services.module_service.ProjectModuleModel")
    def test_no_endpoint_raises(self, mock_pm_model, module):
        mock_pm_model.objects.filter.return_value.first.return_value = None

        with pytest.raises(ManifestValidationError) as exc_info:
            fetch_manifest(module)

        assert "No active endpoint" in str(exc_info.value)

    @patch("core.apps.api.services.module_service.ProjectModuleModel")
    @patch("core.apps.api.services.module_service.requests.post")
    def test_all_allowed_field_types_pass(self, mock_post, mock_pm_model, module, project_module):
        mock_pm_model.objects.filter.return_value.first.return_value = project_module

        fields = [{"name": f"f_{t}", "type": t} for t in ALLOWED_FIELD_TYPES]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {
                "module": "demo",
                "nodes": [{"type": "demo.All", "fields": fields}],
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = fetch_manifest(module)
        assert result is not None
        module.save.assert_called_once()


class TestGetProjectModuleManifests:
    @patch("core.apps.api.services.module_service.ProjectModuleModel")
    def test_returns_manifests_with_meta(self, mock_pm_model):
        mock_module = MagicMock()
        mock_module.slug = "demo"
        mock_module.name = "Demo"
        mock_module.manifest_cache = {
            "module": "demo",
            "nodes": [{"type": "demo.Echo"}],
        }

        pm = MagicMock()
        pm.module = mock_module

        mock_pm_model.objects.filter.return_value.select_related.return_value = [pm]

        project = MagicMock()
        result = get_project_module_manifests(project)

        assert len(result) == 1
        assert result[0]["moduleSlug"] == "demo"
        assert result[0]["moduleName"] == "Demo"
        assert "nodes" in result[0]

    @patch("core.apps.api.services.module_service.ProjectModuleModel")
    def test_skips_empty_cache(self, mock_pm_model):
        mock_module = MagicMock()
        mock_module.manifest_cache = None

        pm = MagicMock()
        pm.module = mock_module

        mock_pm_model.objects.filter.return_value.select_related.return_value = [pm]

        project = MagicMock()
        result = get_project_module_manifests(project)

        assert result == []


class TestGetProjectModulesForEngine:
    @patch("core.apps.api.services.module_service.ProjectModuleModel")
    def test_returns_engine_format(self, mock_pm_model):
        mock_module = MagicMock()
        mock_module.slug = "demo"
        mock_module.auth_token = "tok"
        mock_module.manifest_cache = {
            "nodes": [{"type": "demo.Echo"}, {"type": "demo.Upper"}],
            "triggers": [{"type": "demo.OnMsg", "mode": "event-match"}],
        }

        pm = MagicMock()
        pm.module = mock_module
        pm.endpoint = "http://module-demo-1:8100/rpc"

        mock_pm_model.objects.filter.return_value.select_related.return_value = [pm]

        project = MagicMock()
        result = get_project_modules_for_engine(project)

        assert len(result) == 1
        entry = result[0]
        assert entry["slug"] == "demo"
        assert entry["endpoint"] == "http://module-demo-1:8100/rpc"
        assert entry["auth_token"] == "tok"
        assert "demo.Echo" in entry["nodes"]
        assert "demo.Upper" in entry["nodes"]
        assert entry["triggers"][0]["type"] == "demo.OnMsg"
        assert entry["triggers"][0]["mode"] == "event-match"
