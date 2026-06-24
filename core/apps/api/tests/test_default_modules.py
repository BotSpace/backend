"""Test: is_default modul yangi project yaratilganda avtomatik yoqilishi."""
import pytest
from unittest.mock import MagicMock, patch

from core.apps.api.models.module import ModuleModel, ProjectModuleModel
from core.apps.api.tasks.project import enable_default_modules


@pytest.fixture(autouse=True)
def patch_signal_side_effects():
    """Project yaratish signali k8s va mongo ga tegmasin."""
    with (
        patch("core.apps.api.signals.project.remove_service"),
        patch("core.apps.api.signals.project.deploy_service") as mock_deploy,
        patch("core.apps.api.signals.project.enable_default_modules"),
    ):
        magic = MagicMock()
        magic.metadata.name = "test-deployment"
        mock_deploy.return_value = magic
        yield


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(phone="+998901234567", password="pass")


@pytest.fixture
def project(db, user):
    from core.apps.api.models import ProjectModel

    return ProjectModel.objects.create(name="Test project", owner=user)


@pytest.fixture
def default_module(db):
    return ModuleModel.objects.create(
        slug="test-default-mod",
        name="Test Default Module",
        image="registry.example.com/test:latest",
        port=8100,
        active=True,
        is_default=True,
    )


@pytest.fixture
def non_default_module(db):
    return ModuleModel.objects.create(
        slug="test-non-default-mod",
        name="Test Non-Default Module",
        image="registry.example.com/other:latest",
        port=8100,
        active=True,
        is_default=False,
    )


class TestEnableDefaultModulesTask:
    @patch("core.apps.api.tasks.project.fetch_manifest")
    @patch("core.apps.api.tasks.project.deploy_module")
    def test_default_module_yoqiladi(self, mock_deploy, mock_fetch, db, project, default_module):
        pm = MagicMock()
        pm.id = 1
        mock_deploy.return_value = pm

        enable_default_modules(project.pk)

        mock_deploy.assert_called_once_with(project, default_module)
        mock_fetch.assert_called_once_with(default_module)

    @patch("core.apps.api.tasks.project.fetch_manifest")
    @patch("core.apps.api.tasks.project.deploy_module")
    def test_non_default_module_yoqilmaydi(self, mock_deploy, mock_fetch, db, project, non_default_module):
        enable_default_modules(project.pk)

        mock_deploy.assert_not_called()
        mock_fetch.assert_not_called()

    @patch("core.apps.api.tasks.project.fetch_manifest")
    @patch("core.apps.api.tasks.project.deploy_module")
    def test_allaqachon_enabled_bo_lsa_o_tkazib_yuboriladi(
        self, mock_deploy, mock_fetch, db, project, default_module
    ):
        # Allaqachon yoqilgan holat
        ProjectModuleModel.objects.create(
            project=project,
            module=default_module,
            enabled=True,
            status="running",
            endpoint="http://module-test:8100/rpc",
        )

        enable_default_modules(project.pk)

        mock_deploy.assert_not_called()

    @patch("core.apps.api.tasks.project.fetch_manifest")
    @patch("core.apps.api.tasks.project.deploy_module")
    def test_deploy_xatoligi_task_ni_buzmasin(self, mock_deploy, mock_fetch, db, project, default_module):
        mock_deploy.side_effect = Exception("k8s unavailable")

        # Task exception ko'tarmasligi kerak
        enable_default_modules(project.pk)

        mock_deploy.assert_called_once()
        mock_fetch.assert_not_called()

    @patch("core.apps.api.tasks.project.fetch_manifest")
    @patch("core.apps.api.tasks.project.deploy_module")
    def test_default_modules_yo_q_bo_lsa(self, mock_deploy, mock_fetch, db, project):
        # Hech qanday default modul yo'q
        enable_default_modules(project.pk)

        mock_deploy.assert_not_called()

    @patch("core.apps.api.tasks.project.fetch_manifest")
    @patch("core.apps.api.tasks.project.deploy_module")
    def test_project_topilmasa_xato_yo_q(self, mock_deploy, mock_fetch, db):
        # Mavjud bo'lmagan project_id
        enable_default_modules(99999)

        mock_deploy.assert_not_called()

    @patch("core.apps.api.tasks.project.fetch_manifest")
    @patch("core.apps.api.tasks.project.deploy_module")
    def test_bir_xatolik_boshqa_modulga_ta_sir_qilmasin(
        self, mock_deploy, mock_fetch, db, project, default_module
    ):
        second = ModuleModel.objects.create(
            slug="test-default-mod-2",
            name="Second Default",
            image="registry.example.com/second:latest",
            port=8100,
            active=True,
            is_default=True,
        )

        pm = MagicMock()
        pm.id = 2

        # Birinchi modul yiqiladi, ikkinchisi o'tishi kerak
        def deploy_side_effect(proj, mod):
            if mod.slug == default_module.slug:
                raise Exception("first module failed")
            return pm

        mock_deploy.side_effect = deploy_side_effect

        enable_default_modules(project.pk)

        # Ikkala modul uchun deploy chaqirilishi kerak
        assert mock_deploy.call_count == 2
        # Ikkinchi modul uchun fetch_manifest chaqirilishi kerak
        mock_fetch.assert_called_once_with(second)
