"""
Tests for release deployment cleanup fix.

These tests verify that when a new release is created:
1. Old releases with INIT or RUNNING status are cleaned up
2. The current release is not included in the cleanup
3. Null service_id values are handled gracefully
"""

from unittest.mock import MagicMock, patch, call

import pytest
from core.apps.api.models import RelaseModel, ProjectModel
from core.apps.api.enums.container import ContainerStatusEnum


@pytest.fixture
def project(db):
    """Create a test project"""
    from core.apps.accounts.models import User
    user = User.objects.create_user(
        phone="+998901234567",
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )
    project = ProjectModel.objects.create(
        name="Test Project",
        owner=user,
        flow=[]
    )
    return project


@pytest.mark.django_db
@patch("core.apps.api.signals.project.remove_service")
@patch("core.apps.api.signals.project.deploy_service")
def test_release_cleanup_excludes_current_instance(mock_deploy, mock_remove, project):
    """Test that the current release being created is not included in cleanup"""
    # Setup mock
    mock_deployment = MagicMock()
    mock_deployment.metadata.name = "release-1-1"
    mock_deploy.return_value = mock_deployment
    mock_remove.return_value = True
    
    # Create first release - signal will set it to INIT
    release1 = RelaseModel.objects.create(
        project=project,
        version=1,
        flow=[],
    )
    
    # Manually update to RUNNING to simulate it being deployed
    release1.status = ContainerStatusEnum.RUNNING.value
    release1.service_id = "release-1-1"
    release1.save(update_fields=['status', 'service_id'])
    
    # Reset mocks after first release creation
    mock_remove.reset_mock()
    mock_deploy.reset_mock()
    mock_deployment.metadata.name = "release-1-2"
    
    # Create second release - should trigger cleanup of first release
    release2 = RelaseModel.objects.create(
        project=project,
        version=2,
        flow=[],
    )
    
    # Verify remove_service was called once for the old release
    assert mock_remove.call_count == 1
    mock_remove.assert_called_once_with("release-1-1")
    
    # Verify the old release status was updated to STOPPING
    release1.refresh_from_db()
    assert release1.status == ContainerStatusEnum.STOPPING.value
    
    # Verify the new release has INIT status
    release2.refresh_from_db()
    assert release2.status == ContainerStatusEnum.INIT.value


@pytest.mark.django_db
@patch("core.apps.api.signals.project.remove_service")
@patch("core.apps.api.signals.project.deploy_service")
def test_release_cleanup_handles_null_service_id(mock_deploy, mock_remove, project):
    """Test that releases with null service_id are handled gracefully"""
    # Setup mock
    mock_deployment = MagicMock()
    mock_deployment.metadata.name = "release-1-1"
    mock_deploy.return_value = mock_deployment
    mock_remove.return_value = True
    
    # Create first release - signal sets it to INIT
    release1 = RelaseModel.objects.create(
        project=project,
        version=1,
        flow=[],
    )
    
    # Manually update to RUNNING with NULL service_id
    release1.status = ContainerStatusEnum.RUNNING.value
    release1.service_id = None
    release1.save(update_fields=['status', 'service_id'])
    
    # Reset mocks
    mock_remove.reset_mock()
    mock_deploy.reset_mock()
    mock_deployment.metadata.name = "release-1-2"
    
    # Create second release - should NOT call remove_service for release with null service_id
    release2 = RelaseModel.objects.create(
        project=project,
        version=2,
        flow=[],
    )
    
    # Verify remove_service was NOT called (because service_id was None)
    assert mock_remove.call_count == 0
    
    # Verify the old release status was still updated to STOPPING
    release1.refresh_from_db()
    assert release1.status == ContainerStatusEnum.STOPPING.value


@pytest.mark.django_db
@patch("core.apps.api.signals.project.remove_service")
@patch("core.apps.api.signals.project.deploy_service")
def test_release_cleanup_multiple_old_releases(mock_deploy, mock_remove, project):
    """Test that multiple old releases are all cleaned up"""
    # Setup mock
    mock_deployment = MagicMock()
    mock_deploy.return_value = mock_deployment
    mock_remove.return_value = True
    
    # Don't reset mocks - track all calls across multiple release creations
    
    # Create first release
    mock_deployment.metadata.name = "release-1-1"
    release1 = RelaseModel.objects.create(
        project=project,
        version=1,
        flow=[],
    )
    
    # First release will be deployed by signal, manually mark as RUNNING
    release1.status = ContainerStatusEnum.RUNNING.value
    release1.service_id = "release-1-1"
    release1.save(update_fields=['status', 'service_id'])
    
    # Create second release - this will cleanup release1
    mock_deployment.metadata.name = "release-1-2"
    release2 = RelaseModel.objects.create(
        project=project,
        version=2,
        flow=[],
    )
    
    # After release2 creation:
    # - release1 should be STOPPING (cleaned up)
    # - release2 should be INIT (just created)
    release1.refresh_from_db()
    assert release1.status == ContainerStatusEnum.STOPPING.value
    
    # Manually mark release2 with RUNNING status to test another cleanup
    release2.status = ContainerStatusEnum.RUNNING.value
    release2.service_id = "release-1-2"
    release2.save(update_fields=['status', 'service_id'])
    
    # Create third release - this will cleanup release2 (release1 already STOPPING)
    mock_deployment.metadata.name = "release-1-3"
    release3 = RelaseModel.objects.create(
        project=project,
        version=3,
        flow=[],
    )
    
    # Verify remove_service was called for both old releases across all operations
    assert mock_remove.call_count == 2
    calls = [call("release-1-1"), call("release-1-2")]
    mock_remove.assert_has_calls(calls, any_order=True)
    
    # Verify both old releases have STOPPING status
    release1.refresh_from_db()
    release2.refresh_from_db()
    assert release1.status == ContainerStatusEnum.STOPPING.value
    assert release2.status == ContainerStatusEnum.STOPPING.value


@pytest.mark.django_db
@patch("core.apps.api.signals.project.remove_service")
@patch("core.apps.api.signals.project.deploy_service")
def test_release_cleanup_only_affects_running_and_init(mock_deploy, mock_remove, project):
    """Test that only releases with RUNNING or INIT status are cleaned up"""
    # Setup mock
    mock_deployment = MagicMock()
    mock_deployment.metadata.name = "release-1-1"
    mock_deploy.return_value = mock_deployment
    mock_remove.return_value = True
    
    # Create first release
    release1 = RelaseModel.objects.create(
        project=project,
        version=1,
        flow=[],
    )
    
    # Manually update to STOPPED status - should NOT be cleaned up
    release1.status = ContainerStatusEnum.STOPPED.value
    release1.service_id = "release-1-1"
    release1.save(update_fields=['status', 'service_id'])
    
    mock_deployment.metadata.name = "release-1-2"
    release2 = RelaseModel.objects.create(
        project=project,
        version=2,
        flow=[],
    )
    
    # Manually update to RUNNING
    release2.status = ContainerStatusEnum.RUNNING.value
    release2.service_id = "release-1-2"
    release2.save(update_fields=['status', 'service_id'])
    
    # Reset mocks
    mock_remove.reset_mock()
    mock_deploy.reset_mock()
    mock_deployment.metadata.name = "release-1-3"
    
    # Create third release
    release3 = RelaseModel.objects.create(
        project=project,
        version=3,
        flow=[],
    )
    
    # Verify remove_service was called only once for the RUNNING release
    assert mock_remove.call_count == 1
    mock_remove.assert_called_once_with("release-1-2")
    
    # Verify only the RUNNING release status was updated
    release1.refresh_from_db()
    release2.refresh_from_db()
    assert release1.status == ContainerStatusEnum.STOPPED.value  # Unchanged
    assert release2.status == ContainerStatusEnum.STOPPING.value  # Changed
