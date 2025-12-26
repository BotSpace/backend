"""
Tests for Kubernetes engine service
"""
import pytest
from unittest.mock import patch, MagicMock

from core.apps.api.enums.container import ContainerStatusEnum


class TestKubernetesService:
    """Test Kubernetes engine deployment management"""

    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.services.kubernetes_service.get_namespace', return_value='botmother')
    def test_create_deployment(self, mock_get_namespace, mock_apps_api_class):
        """Test creating Kubernetes deployment for engine"""
        from core.apps.api.services.kubernetes_service import create_deployment
        
        # Setup mock
        mock_apps_api = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.metadata.name = "test-deployment"
        mock_apps_api.create_namespaced_deployment.return_value = mock_deployment
        mock_apps_api_class.return_value = mock_apps_api
        
        # Create deployment
        deployment = create_deployment(
            image="registry.jscorp.uz/golang-engine:v1",
            name="test-deployment",
            env_vars=["API_URL=http://localhost:8000"]
        )
        
        # Verify deployment creation was called
        assert mock_apps_api.create_namespaced_deployment.called
        call_kwargs = mock_apps_api.create_namespaced_deployment.call_args[1]
        assert call_kwargs["namespace"] == "botmother"

    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.services.kubernetes_service.get_namespace', return_value='botmother')
    def test_remove_deployment(self, mock_get_namespace, mock_apps_api_class):
        """Test removing Kubernetes deployment"""
        from core.apps.api.services.kubernetes_service import remove_deployment
        
        mock_apps_api = MagicMock()
        mock_apps_api_class.return_value = mock_apps_api
        
        result = remove_deployment("test-deployment")
        
        # Verify delete was called
        mock_apps_api.delete_namespaced_deployment.assert_called_once_with(
            name="test-deployment",
            namespace="botmother"
        )
        assert result is True

    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.services.kubernetes_service.get_namespace', return_value='botmother')
    def test_get_deployment_status_running(self, mock_get_namespace, mock_apps_api_class):
        """Test getting deployment status when running"""
        from core.apps.api.services.kubernetes_service import get_deployment_status
        
        mock_apps_api = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.status.ready_replicas = 1
        mock_deployment.status.replicas = 1
        mock_apps_api.read_namespaced_deployment.return_value = mock_deployment
        mock_apps_api_class.return_value = mock_apps_api
        
        status = get_deployment_status("test-deployment")
        
        assert status == ContainerStatusEnum.RUNNING.value

    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.services.kubernetes_service.get_namespace', return_value='botmother')
    def test_get_deployment_status_pending(self, mock_get_namespace, mock_apps_api_class):
        """Test getting deployment status when pending"""
        from core.apps.api.services.kubernetes_service import get_deployment_status
        
        mock_apps_api = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.status.ready_replicas = 0
        mock_deployment.status.replicas = 1
        mock_apps_api.read_namespaced_deployment.return_value = mock_deployment
        mock_apps_api_class.return_value = mock_apps_api
        
        status = get_deployment_status("test-deployment")
        
        assert status == ContainerStatusEnum.INIT.value

    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.services.kubernetes_service.get_namespace', return_value='botmother')
    def test_get_deployment_status_stopped(self, mock_get_namespace, mock_apps_api_class):
        """Test getting deployment status when stopped"""
        from core.apps.api.services.kubernetes_service import get_deployment_status
        
        mock_apps_api = MagicMock()
        mock_deployment = MagicMock()
        mock_deployment.status.ready_replicas = 0
        mock_deployment.status.replicas = 0
        mock_apps_api.read_namespaced_deployment.return_value = mock_deployment
        mock_apps_api_class.return_value = mock_apps_api
        
        status = get_deployment_status("test-deployment")
        
        assert status == ContainerStatusEnum.STOPPED.value

    def test_convert_k8s_event_status(self):
        """Test converting Kubernetes events to container status"""
        from core.apps.api.services.kubernetes_service import convert_k8s_event_status
        
        # Test running status
        assert convert_k8s_event_status("MODIFIED", "running") == ContainerStatusEnum.RUNNING.value
        assert convert_k8s_event_status("MODIFIED", "started") == ContainerStatusEnum.RUNNING.value
        
        # Test init/pending status
        assert convert_k8s_event_status("ADDED", "pending") == ContainerStatusEnum.INIT.value
        assert convert_k8s_event_status("MODIFIED", "scheduled") == ContainerStatusEnum.INIT.value
        
        # Test failed status
        assert convert_k8s_event_status("MODIFIED", "failed") == ContainerStatusEnum.FAILED.value
        assert convert_k8s_event_status("MODIFIED", "oomkilled") == ContainerStatusEnum.FAILED.value
        
        # Test deleted/stopped status
        assert convert_k8s_event_status("DELETED", "running") == ContainerStatusEnum.STOPPED.value

    @patch('core.apps.api.services.kubernetes_service.get_k8s_client')
    @patch('core.apps.api.services.kubernetes_service.get_namespace', return_value='botmother')
    def test_create_configmap(self, mock_get_namespace, mock_get_client):
        """Test creating ConfigMap for flow"""
        from core.apps.api.services.kubernetes_service import create_configmap
        
        mock_api = MagicMock()
        mock_get_client.return_value = mock_api
        
        create_configmap("test-flow", {"flow.json": '{"nodes": []}'})
        
        # Verify ConfigMap creation was called
        assert mock_api.create_namespaced_config_map.called

    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.services.kubernetes_service.get_namespace', return_value='botmother')
    def test_stop_project_deployments(self, mock_get_namespace, mock_apps_api_class):
        """Test stopping all deployments for a project"""
        from core.apps.api.services.kubernetes_service import stop_project_deployments
        
        mock_apps_api = MagicMock()
        mock_deployment1 = MagicMock()
        mock_deployment1.metadata.name = "debug-123"
        mock_deployment2 = MagicMock()
        mock_deployment2.metadata.name = "release-123-1"
        
        mock_deployments = MagicMock()
        mock_deployments.items = [mock_deployment1, mock_deployment2]
        mock_apps_api.list_namespaced_deployment.return_value = mock_deployments
        mock_apps_api_class.return_value = mock_apps_api
        
        count = stop_project_deployments(123)
        
        assert count == 2
        assert mock_apps_api.delete_namespaced_deployment.call_count == 2


class TestDockerServiceWrapper:
    """Test Docker service wrapper functions that delegate to Kubernetes"""

    @patch('core.apps.api.services.docker_service.get_deployment_status')
    def test_get_service_status(self, mock_get_deployment_status):
        """Test that get_service_status delegates to Kubernetes"""
        from core.apps.api.services.docker_service import get_service_status
        
        mock_get_deployment_status.return_value = ContainerStatusEnum.RUNNING.value
        
        status = get_service_status("test-deployment")
        mock_get_deployment_status.assert_called_once_with("test-deployment")
        assert status == ContainerStatusEnum.RUNNING.value

    @patch('core.apps.api.services.docker_service.remove_deployment')
    def test_remove_service(self, mock_remove_deployment):
        """Test that remove_service delegates to Kubernetes"""
        from core.apps.api.services.docker_service import remove_service
        
        mock_remove_deployment.return_value = True
        
        result = remove_service("test-deployment")
        mock_remove_deployment.assert_called_once_with("test-deployment")
        assert result is True

    @patch('core.apps.api.services.docker_service.stop_project_deployments')
    def test_stop_project_services(self, mock_stop_deployments):
        """Test that stop_project_services delegates to Kubernetes"""
        from core.apps.api.services.docker_service import stop_project_services
        
        mock_stop_deployments.return_value = 2
        
        count = stop_project_services(123)
        mock_stop_deployments.assert_called_once_with(123)
        assert count == 2
