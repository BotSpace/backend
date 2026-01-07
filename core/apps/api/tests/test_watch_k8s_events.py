"""
Tests for Kubernetes event watcher command
"""
import pytest
from unittest.mock import patch, MagicMock, call
from io import StringIO
from kubernetes.client.rest import ApiException

from django.core.management import call_command
from core.apps.api.enums.container import ContainerStatusEnum


class TestWatchK8sEventsCommand:
    """Test Kubernetes event watcher management command"""

    @patch('core.apps.api.management.commands.watch_k8s_events.time.sleep')
    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace', return_value='botmother')
    def test_watch_with_reconnect_on_timeout(self, mock_get_namespace, mock_apps_api_class, mock_load_config, mock_sleep):
        """Test that watcher reconnects after timeout"""
        from core.apps.api.management.commands.watch_k8s_events import Command
        
        mock_apps_api = MagicMock()
        mock_apps_api_class.return_value = mock_apps_api
        
        # Simulate stream ending after timeout (3 times then raise KeyboardInterrupt)
        call_count = [0]
        
        def stream_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise KeyboardInterrupt()
            return iter([])  # Empty iterator simulates timeout
            
        with patch('kubernetes.watch.Watch.stream', side_effect=stream_side_effect):
            cmd = Command()
            try:
                cmd.handle(namespace='botmother', label_selector='app=test', verbose=False, timeout=300)
            except KeyboardInterrupt:
                pass
        
        # Should have called stream 3 times (2 reconnects)
        assert call_count[0] == 3

    @patch('core.apps.api.management.commands.watch_k8s_events.time.sleep')
    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace', return_value='botmother')
    def test_watch_with_reconnect_on_410_error(self, mock_get_namespace, mock_apps_api_class, mock_load_config, mock_sleep):
        """Test that watcher reconnects immediately on 410 Gone error (resource version expired)"""
        from core.apps.api.management.commands.watch_k8s_events import Command
        
        mock_apps_api = MagicMock()
        mock_apps_api_class.return_value = mock_apps_api
        
        call_count = [0]
        
        def stream_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call raises 410 error
                raise ApiException(status=410, reason="Gone")
            elif call_count[0] >= 2:
                # Second call succeeds then we stop
                raise KeyboardInterrupt()
            return iter([])
            
        with patch('kubernetes.watch.Watch.stream', side_effect=stream_side_effect):
            cmd = Command()
            try:
                cmd.handle(namespace='botmother', label_selector='app=test', verbose=False, timeout=300)
            except KeyboardInterrupt:
                pass
        
        # Should have reconnected after 410 error
        assert call_count[0] >= 2
        # Should not have slept on first reconnect (410 errors get immediate retry)
        assert mock_sleep.call_count == 0

    @patch('core.apps.api.management.commands.watch_k8s_events.time.sleep')
    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace', return_value='botmother')
    def test_watch_with_exponential_backoff(self, mock_get_namespace, mock_apps_api_class, mock_load_config, mock_sleep):
        """Test that watcher uses exponential backoff on errors"""
        from core.apps.api.management.commands.watch_k8s_events import Command
        
        mock_apps_api = MagicMock()
        mock_apps_api_class.return_value = mock_apps_api
        
        call_count = [0]
        
        def stream_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 4:
                raise KeyboardInterrupt()
            # Raise a different error to trigger backoff
            raise ApiException(status=500, reason="Internal Server Error")
            
        with patch('kubernetes.watch.Watch.stream', side_effect=stream_side_effect):
            cmd = Command()
            try:
                cmd.handle(namespace='botmother', label_selector='app=test', verbose=False, timeout=300)
            except KeyboardInterrupt:
                pass
        
        # Should have called sleep with exponential backoff: 2, 4, 8 seconds
        assert mock_sleep.call_count >= 3
        sleep_calls = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        # Verify exponential backoff: 2^1=2, 2^2=4, 2^3=8
        assert sleep_calls[0] == 2
        assert sleep_calls[1] == 4
        assert sleep_calls[2] == 8

    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace', return_value='botmother')
    def test_process_event_updates_debug_status(self, mock_get_namespace, mock_apps_api_class, mock_load_config):
        """Test that deployment events update debug service status in database"""
        from core.apps.api.management.commands.watch_k8s_events import Command
        from core.apps.api.models.project import DebugModel
        
        # Create a mock debug service
        mock_debug = MagicMock(spec=DebugModel)
        mock_debug.status = ContainerStatusEnum.INIT.value
        mock_debug.service_id = "debug-test-123"
        
        # Mock deployment event
        mock_deployment = MagicMock()
        mock_deployment.metadata.name = "debug-test-123"
        mock_deployment.metadata.labels = {"engine-name": "debug-test-123"}
        mock_deployment.status.ready_replicas = 1
        mock_deployment.status.replicas = 1
        
        event = {
            "type": "MODIFIED",
            "object": mock_deployment
        }
        
        cmd = Command()
        
        with patch.object(DebugModel.objects, 'get', return_value=mock_debug):
            with patch.object(cmd, '_send_ws_notification'):
                cmd._process_event(event, verbose=False)
        
        # Status should have been updated to RUNNING
        assert mock_debug.status == ContainerStatusEnum.RUNNING.value
        mock_debug.save.assert_called_once()

    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace', return_value='botmother')
    def test_process_event_handles_pending_deployment(self, mock_get_namespace, mock_apps_api_class, mock_load_config):
        """Test that pending deployment (replicas > 0, ready = 0) is detected"""
        from core.apps.api.management.commands.watch_k8s_events import Command
        from core.apps.api.models.project import RelaseModel
        
        # Create a mock release service
        mock_release = MagicMock(spec=RelaseModel)
        mock_release.status = ContainerStatusEnum.STOPPED.value
        mock_release.service_id = "release-test-456"
        
        # Mock deployment event - deployment is pending (has replicas but none ready)
        mock_deployment = MagicMock()
        mock_deployment.metadata.name = "release-test-456"
        mock_deployment.metadata.labels = {"engine-name": "release-test-456"}
        mock_deployment.status.ready_replicas = 0
        mock_deployment.status.replicas = 1  # Replicas exist but not ready
        
        event = {
            "type": "MODIFIED",
            "object": mock_deployment
        }
        
        cmd = Command()
        
        with patch.object(RelaseModel.objects, 'get', return_value=mock_release):
            with patch.object(cmd, '_send_ws_notification'):
                cmd._process_event(event, verbose=False)
        
        # Status should have been updated to INIT (pending)
        assert mock_release.status == ContainerStatusEnum.INIT.value
        mock_release.save.assert_called_once()

    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace', return_value='botmother')
    def test_process_event_handles_deleted_deployment(self, mock_get_namespace, mock_apps_api_class, mock_load_config):
        """Test that DELETED events update status to STOPPED"""
        from core.apps.api.management.commands.watch_k8s_events import Command
        from core.apps.api.models.project import DebugModel
        
        # Create a mock debug service
        mock_debug = MagicMock(spec=DebugModel)
        mock_debug.status = ContainerStatusEnum.RUNNING.value
        mock_debug.service_id = "debug-test-789"
        
        # Mock deployment event
        mock_deployment = MagicMock()
        mock_deployment.metadata.name = "debug-test-789"
        mock_deployment.metadata.labels = {"engine-name": "debug-test-789"}
        mock_deployment.status.ready_replicas = 0
        mock_deployment.status.replicas = 0
        
        event = {
            "type": "DELETED",
            "object": mock_deployment
        }
        
        cmd = Command()
        
        with patch.object(DebugModel.objects, 'get', return_value=mock_debug):
            with patch.object(cmd, '_send_ws_notification'):
                cmd._process_event(event, verbose=False)
        
        # Status should have been updated to STOPPED
        assert mock_debug.status == ContainerStatusEnum.STOPPED.value
        mock_debug.save.assert_called_once()

    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace', return_value='botmother')
    def test_process_event_ignores_deployments_without_engine_label(self, mock_get_namespace, mock_apps_api_class, mock_load_config):
        """Test that deployments without engine-name label are ignored"""
        from core.apps.api.management.commands.watch_k8s_events import Command
        
        # Mock deployment without engine-name label
        mock_deployment = MagicMock()
        mock_deployment.metadata.name = "some-other-deployment"
        mock_deployment.metadata.labels = {"app": "other-app"}
        
        event = {
            "type": "MODIFIED",
            "object": mock_deployment
        }
        
        cmd = Command()
        
        # Should not raise any exceptions and not query database
        cmd._process_event(event, verbose=False)
        # Test passes if no exception is raised

    @patch('kubernetes.watch.Watch.stop')
    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace', return_value='botmother')
    def test_watch_stops_properly(self, mock_get_namespace, mock_apps_api_class, mock_load_config, mock_watch_stop):
        """Test that watch is stopped properly even on errors"""
        from core.apps.api.management.commands.watch_k8s_events import Command
        
        mock_apps_api = MagicMock()
        mock_apps_api_class.return_value = mock_apps_api
        
        # Simulate an error during streaming
        def stream_side_effect(*args, **kwargs):
            raise RuntimeError("Test error")
            
        with patch('kubernetes.watch.Watch.stream', side_effect=stream_side_effect):
            cmd = Command()
            try:
                cmd._watch_events('botmother', 'app=test', False, 300)
            except RuntimeError:
                pass
        
        # Watch should have been stopped
        mock_watch_stop.assert_called_once()
