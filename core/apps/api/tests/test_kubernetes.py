"""
Tests for Kubernetes engine service
"""
import pytest
from unittest.mock import patch, MagicMock

from core.apps.api.enums.container import ContainerStatusEnum


@pytest.mark.django_db
class TestKubernetesService:
    """Test Kubernetes engine pod management"""

    @patch('core.apps.api.services.kubernetes_service.get_k8s_client')
    def test_create_pod(self, mock_get_client):
        """Test creating Kubernetes pod for engine"""
        from core.apps.api.services.kubernetes_service import create_pod
        
        # Setup mock
        mock_api = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_api.create_namespaced_pod.return_value = mock_pod
        mock_get_client.return_value = mock_api
        
        # Create pod
        pod = create_pod(
            image="registry.jscorp.uz/golang-engine:v1",
            name="test-pod",
            env_vars=["API_URL=http://localhost:8000"]
        )
        
        # Verify pod creation was called
        assert mock_api.create_namespaced_pod.called
        call_kwargs = mock_api.create_namespaced_pod.call_args[1]
        assert call_kwargs["namespace"] == "botmother"

    @patch('core.apps.api.services.kubernetes_service.get_k8s_client')
    def test_remove_pod(self, mock_get_client):
        """Test removing Kubernetes pod"""
        from core.apps.api.services.kubernetes_service import remove_pod
        
        mock_api = MagicMock()
        mock_get_client.return_value = mock_api
        
        result = remove_pod("test-pod")
        
        # Verify delete was called
        mock_api.delete_namespaced_pod.assert_called_once_with(
            name="test-pod",
            namespace="botmother"
        )
        assert result is True

    @patch('core.apps.api.services.kubernetes_service.get_k8s_client')
    def test_get_pod_status_running(self, mock_get_client):
        """Test getting pod status when running"""
        from core.apps.api.services.kubernetes_service import get_pod_status
        
        mock_api = MagicMock()
        mock_pod = MagicMock()
        mock_pod.status.phase = "Running"
        mock_api.read_namespaced_pod.return_value = mock_pod
        mock_get_client.return_value = mock_api
        
        status = get_pod_status("test-pod")
        
        assert status == ContainerStatusEnum.RUNNING.value

    @patch('core.apps.api.services.kubernetes_service.get_k8s_client')
    def test_get_pod_status_pending(self, mock_get_client):
        """Test getting pod status when pending"""
        from core.apps.api.services.kubernetes_service import get_pod_status
        
        mock_api = MagicMock()
        mock_pod = MagicMock()
        mock_pod.status.phase = "Pending"
        mock_api.read_namespaced_pod.return_value = mock_pod
        mock_get_client.return_value = mock_api
        
        status = get_pod_status("test-pod")
        
        assert status == ContainerStatusEnum.INIT.value

    @patch('core.apps.api.services.kubernetes_service.get_k8s_client')
    def test_get_pod_status_failed(self, mock_get_client):
        """Test getting pod status when failed"""
        from core.apps.api.services.kubernetes_service import get_pod_status
        
        mock_api = MagicMock()
        mock_pod = MagicMock()
        mock_pod.status.phase = "Failed"
        mock_api.read_namespaced_pod.return_value = mock_pod
        mock_get_client.return_value = mock_api
        
        status = get_pod_status("test-pod")
        
        assert status == ContainerStatusEnum.FAILED.value

    def test_convert_k8s_event_status(self):
        """Test converting Kubernetes events to container status"""
        from core.apps.api.services.kubernetes_service import convert_k8s_event_status
        
        # Test running status
        assert convert_k8s_event_status("MODIFIED", "Running") == ContainerStatusEnum.RUNNING.value
        assert convert_k8s_event_status("MODIFIED", "Started") == ContainerStatusEnum.RUNNING.value
        
        # Test init/pending status
        assert convert_k8s_event_status("ADDED", "Pending") == ContainerStatusEnum.INIT.value
        assert convert_k8s_event_status("MODIFIED", "Scheduled") == ContainerStatusEnum.INIT.value
        
        # Test failed status
        assert convert_k8s_event_status("MODIFIED", "Failed") == ContainerStatusEnum.FAILED.value
        assert convert_k8s_event_status("MODIFIED", "OOMKilled") == ContainerStatusEnum.FAILED.value
        
        # Test deleted/stopped status
        assert convert_k8s_event_status("DELETED", "Running") == ContainerStatusEnum.STOPPED.value

    @patch('core.apps.api.services.kubernetes_service.get_k8s_client')
    def test_create_configmap(self, mock_get_client):
        """Test creating ConfigMap for flow"""
        from core.apps.api.services.kubernetes_service import create_configmap
        
        mock_api = MagicMock()
        mock_get_client.return_value = mock_api
        
        create_configmap("test-flow", {"flow.json": '{"nodes": []}'})
        
        # Verify ConfigMap creation was called
        assert mock_api.create_namespaced_config_map.called

    @patch('core.apps.api.services.kubernetes_service.get_k8s_client')
    @patch('core.apps.api.services.kubernetes_service.create_configmap')
    def test_deploy_engine(self, mock_create_configmap, mock_get_client):
        """Test deploying engine pod"""
        from core.apps.api.services.kubernetes_service import deploy_engine
        from core.apps.api.models import ProjectModel
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Setup mocks
        mock_api = MagicMock()
        mock_pod = MagicMock()
        mock_pod.metadata.name = "debug-1"
        mock_api.create_namespaced_pod.return_value = mock_pod
        mock_get_client.return_value = mock_api
        
        # Create project
        user = User._create_fake()
        project = ProjectModel._create_fake(owner=user)
        
        # Mock project's get_mongo_credentials
        with patch.object(project, 'get_mongo_credentials') as mock_get_creds:
            mock_get_creds.return_value = {
                "username": f"project_{project.id}_user",
                "password": "test_pass",
                "database": f"project_{project.id}",
                "connection_string": f"mongodb://project_{project.id}_user:test_pass@localhost:27017/project_{project.id}"
            }
            
            pod = deploy_engine(
                project=project,
                prefix="debug",
                flow={"nodes": [], "edges": []},
                key=str(project.id)
            )
            
            # Verify ConfigMap was created
            mock_create_configmap.assert_called_once()
            
            # Verify pod was created
            assert mock_api.create_namespaced_pod.called

    @patch('core.apps.api.services.kubernetes_service.get_k8s_client')
    def test_stop_project_pods(self, mock_get_client):
        """Test stopping all pods for a project"""
        from core.apps.api.services.kubernetes_service import stop_project_pods
        
        mock_api = MagicMock()
        mock_pod1 = MagicMock()
        mock_pod1.metadata.name = "debug-123"
        mock_pod2 = MagicMock()
        mock_pod2.metadata.name = "release-123-1"
        
        mock_pods = MagicMock()
        mock_pods.items = [mock_pod1, mock_pod2]
        mock_api.list_namespaced_pod.return_value = mock_pods
        mock_get_client.return_value = mock_api
        
        count = stop_project_pods(123)
        
        assert count == 2
        assert mock_api.delete_namespaced_pod.call_count == 2


@pytest.mark.django_db
class TestDockerServiceKubernetesSwitch:
    """Test Docker service functions with Kubernetes switch"""

    @patch('core.apps.api.services.docker_service.ORCHESTRATOR', 'kubernetes')
    @patch('core.apps.api.services.kubernetes_service.get_pod_status')
    def test_get_service_status_uses_kubernetes(self, mock_get_pod_status):
        """Test that get_service_status uses Kubernetes when ORCHESTRATOR=kubernetes"""
        from core.apps.api.services.docker_service import get_service_status, is_kubernetes
        
        mock_get_pod_status.return_value = ContainerStatusEnum.RUNNING.value
        
        # Force is_kubernetes to return True
        with patch('core.apps.api.services.docker_service.is_kubernetes', return_value=True):
            status = get_service_status("test-pod")
            mock_get_pod_status.assert_called_once_with("test-pod")
            assert status == ContainerStatusEnum.RUNNING.value

    @patch('core.apps.api.services.docker_service.ORCHESTRATOR', 'kubernetes')
    @patch('core.apps.api.services.kubernetes_service.remove_pod')
    def test_remove_service_uses_kubernetes(self, mock_remove_pod):
        """Test that remove_service uses Kubernetes when ORCHESTRATOR=kubernetes"""
        from core.apps.api.services.docker_service import remove_service
        
        mock_remove_pod.return_value = True
        
        with patch('core.apps.api.services.docker_service.is_kubernetes', return_value=True):
            result = remove_service("test-pod")
            mock_remove_pod.assert_called_once_with("test-pod")
            assert result is True

    @patch('core.apps.api.services.docker_service.ORCHESTRATOR', 'kubernetes')
    @patch('core.apps.api.services.kubernetes_service.deploy_engine')
    def test_deploy_service_uses_kubernetes(self, mock_deploy_engine):
        """Test that deploy_service uses Kubernetes when ORCHESTRATOR=kubernetes"""
        from core.apps.api.services.docker_service import deploy_service
        from core.apps.api.models import ProjectModel
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        mock_deploy_engine.return_value = mock_pod
        
        user = User._create_fake()
        project = ProjectModel._create_fake(owner=user)
        
        with patch('core.apps.api.services.docker_service.is_kubernetes', return_value=True):
            result = deploy_service(
                project=project,
                prefix="debug",
                flow={"nodes": []},
                key=str(project.id)
            )
            
            mock_deploy_engine.assert_called_once()
            assert result.metadata.name == "test-pod"

    def test_is_kubernetes_returns_false_by_default(self):
        """Test that is_kubernetes returns False by default"""
        from core.apps.api.services.docker_service import is_kubernetes
        
        # Default should be docker (False)
        # Note: This test depends on ORCHESTRATOR env var not being set to kubernetes
        with patch('core.apps.api.services.docker_service.ORCHESTRATOR', 'docker'):
            from core.apps.api.services import docker_service
            docker_service.ORCHESTRATOR = 'docker'
            assert docker_service.is_kubernetes() is False
