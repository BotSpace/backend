"""
Tests for recreate_releases management command
"""

from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import ProjectModel, RelaseModel


# --- GLOBAL PATCH FIXTURE ---
@pytest.fixture(autouse=True)
def patch_docker_services():
    with patch("core.apps.api.signals.project.remove_service") as mock_remove, patch(
        "core.apps.api.signals.project.deploy_service"
    ) as mock_deploy, patch(
        "core.apps.api.signals.project.invalidate_webhook_cache"
    ):
        magic = MagicMock()
        magic.metadata.name = "test-deployment-123"
        mock_deploy.return_value = magic
        mock_remove.return_value = True
        yield


class TestRecreateReleasesCommand:
    """Test recreate_releases management command"""

    @pytest.mark.django_db
    @patch("core.apps.api.management.commands.recreate_releases.deploy_service")
    @patch("core.apps.api.management.commands.recreate_releases.remove_service")
    @patch("core.apps.api.management.commands.recreate_releases.invalidate_webhook_cache")
    def test_recreate_all_releases(self, mock_invalidate_cache, mock_remove, mock_deploy):
        """Test recreating all releases"""
        # Setup mocks
        mock_service = MagicMock()
        mock_service.metadata.name = "new-test-deployment"
        mock_deploy.return_value = mock_service
        mock_remove.return_value = True

        # Create test data
        project1 = ProjectModel._create_fake()
        project2 = ProjectModel._create_fake()

        release1 = RelaseModel.objects.create(
            project=project1, version=1, flow=[], service_id="old-service-1", status=ContainerStatusEnum.RUNNING.value
        )
        release2 = RelaseModel.objects.create(
            project=project2, version=1, flow=[], service_id="old-service-2", status=ContainerStatusEnum.RUNNING.value
        )

        # Run command
        out = StringIO()
        call_command("recreate_releases", stdout=out)

        # Verify deploy_service was called for each project
        assert mock_deploy.call_count == 2

        # Verify remove_service was called for old services
        assert mock_remove.call_count == 2
        mock_remove.assert_any_call("old-service-1")
        mock_remove.assert_any_call("old-service-2")

        # Verify cache was invalidated
        assert mock_invalidate_cache.call_count == 2

        # Verify releases were updated
        release1.refresh_from_db()
        release2.refresh_from_db()
        assert release1.service_id == "new-test-deployment"
        assert release2.service_id == "new-test-deployment"
        assert release1.status == ContainerStatusEnum.INIT.value
        assert release2.status == ContainerStatusEnum.INIT.value

    @pytest.mark.django_db
    @patch("core.apps.api.management.commands.recreate_releases.deploy_service")
    @patch("core.apps.api.management.commands.recreate_releases.remove_service")
    def test_recreate_releases_by_project(self, mock_remove, mock_deploy):
        """Test recreating releases for specific project"""
        # Setup mocks
        mock_service = MagicMock()
        mock_service.metadata.name = "new-test-deployment"
        mock_deploy.return_value = mock_service
        mock_remove.return_value = True

        # Create test data
        project1 = ProjectModel._create_fake()
        project2 = ProjectModel._create_fake()

        RelaseModel.objects.create(
            project=project1, version=1, flow=[], service_id="old-service-1", status=ContainerStatusEnum.RUNNING.value
        )
        RelaseModel.objects.create(
            project=project2, version=1, flow=[], service_id="old-service-2", status=ContainerStatusEnum.RUNNING.value
        )

        # Run command for specific project
        out = StringIO()
        call_command("recreate_releases", project=project1.id, stdout=out)

        # Verify deploy_service was called only once
        assert mock_deploy.call_count == 1

        # Verify remove_service was called only for project1's service
        mock_remove.assert_called_once_with("old-service-1")

    @pytest.mark.django_db
    @patch("core.apps.api.management.commands.recreate_releases.deploy_service")
    @patch("core.apps.api.management.commands.recreate_releases.remove_service")
    def test_recreate_releases_only_latest_per_project(self, mock_remove, mock_deploy):
        """Test that only latest release per project is recreated"""
        # Setup mocks
        mock_service = MagicMock()
        mock_service.metadata.name = "new-test-deployment"
        mock_deploy.return_value = mock_service
        mock_remove.return_value = True

        # Create test data - same project with multiple releases
        project = ProjectModel._create_fake()

        RelaseModel.objects.create(
            project=project, version=1, flow=[], service_id="old-service-v1", status=ContainerStatusEnum.STOPPED.value
        )
        release_v2 = RelaseModel.objects.create(
            project=project, version=2, flow=[], service_id="old-service-v2", status=ContainerStatusEnum.RUNNING.value
        )

        # Run command
        out = StringIO()
        call_command("recreate_releases", stdout=out)

        # Verify deploy_service was called only once (for latest version)
        assert mock_deploy.call_count == 1

        # Verify only the latest version's service was removed
        mock_remove.assert_called_once_with("old-service-v2")

        # Verify only latest release was updated
        release_v2.refresh_from_db()
        assert release_v2.service_id == "new-test-deployment"

    @pytest.mark.django_db
    @patch("core.apps.api.management.commands.recreate_releases.deploy_service")
    @patch("core.apps.api.management.commands.recreate_releases.remove_service")
    def test_recreate_releases_dry_run(self, mock_remove, mock_deploy):
        """Test dry run mode doesn't make actual changes"""
        # Create test data
        project = ProjectModel._create_fake()
        release = RelaseModel.objects.create(
            project=project,
            version=1,
            flow=[],
            service_id="old-service",
            status=ContainerStatusEnum.RUNNING.value,
        )

        original_service_id = release.service_id
        original_status = release.status

        # Run command with dry-run
        out = StringIO()
        call_command("recreate_releases", dry_run=True, stdout=out)

        # Verify no deploy/remove was called
        mock_deploy.assert_not_called()
        mock_remove.assert_not_called()

        # Verify release was not changed
        release.refresh_from_db()
        assert release.service_id == original_service_id
        assert release.status == original_status

    @pytest.mark.django_db
    @patch("core.apps.api.management.commands.recreate_releases.deploy_service")
    @patch("core.apps.api.management.commands.recreate_releases.remove_service")
    def test_recreate_releases_handles_errors(self, mock_remove, mock_deploy):
        """Test command handles deployment errors gracefully"""
        # Setup mocks - deploy_service raises exception
        mock_remove.return_value = True
        mock_deploy.side_effect = Exception("Deployment failed")

        # Create test data
        project = ProjectModel._create_fake()
        RelaseModel.objects.create(
            project=project,
            version=1,
            flow=[],
            service_id="old-service",
            status=ContainerStatusEnum.RUNNING.value,
        )

        # Run command - should not raise exception
        out = StringIO()
        err = StringIO()
        call_command("recreate_releases", stdout=out, stderr=err)

        # Verify error was logged but command completed
        output = out.getvalue()
        assert "Failed:" in output or err.getvalue()

    @pytest.mark.django_db
    def test_recreate_releases_no_releases(self):
        """Test command with no releases"""
        out = StringIO()
        call_command("recreate_releases", stdout=out)

        output = out.getvalue()
        assert "No releases found" in output

    @pytest.mark.django_db
    @patch("core.apps.api.management.commands.recreate_releases.deploy_service")
    @patch("core.apps.api.management.commands.recreate_releases.remove_service")
    def test_recreate_releases_without_service_id(self, mock_remove, mock_deploy):
        """Test recreating release that doesn't have service_id yet"""
        # Setup mocks
        mock_service = MagicMock()
        mock_service.metadata.name = "new-test-deployment"
        mock_deploy.return_value = mock_service

        # Create test data - release without service_id
        project = ProjectModel._create_fake()
        release = RelaseModel.objects.create(
            project=project, version=1, flow=[], status=ContainerStatusEnum.PENDING.value
        )

        # Run command
        out = StringIO()
        call_command("recreate_releases", stdout=out)

        # Verify remove_service was not called (no service_id to remove)
        mock_remove.assert_not_called()

        # Verify deploy_service was still called
        assert mock_deploy.call_count == 1

        # Verify release was updated
        release.refresh_from_db()
        assert release.service_id == "new-test-deployment"
