"""
Tests for Kubernetes event watcher command
"""
from unittest.mock import patch, MagicMock
from kubernetes.client.rest import ApiException

from core.apps.api.enums.container import ContainerStatusEnum


class TestWatchK8sEventsCommand:
    """Test Kubernetes event watcher management command"""

    @patch('core.apps.api.management.commands.watch_k8s_events.time.sleep')
    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace',
           return_value='botmother')
    def test_watch_with_reconnect_on_timeout(
            self, mock_get_namespace, mock_apps_api_class, mock_load_config, mock_sleep):
        """Test that watcher reconnects after timeout"""
        from core.apps.api.management.commands.watch_k8s_events import Command

        mock_apps_api = MagicMock()
        mock_apps_api_class.return_value = mock_apps_api

        call_count = [0]

        def stream_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise KeyboardInterrupt()
            return iter([])

        mock_watch_instance = MagicMock()
        mock_watch_instance.stream.side_effect = stream_side_effect
        with patch('kubernetes.watch.Watch', return_value=mock_watch_instance):
            cmd = Command()
            try:
                cmd.handle(namespace='botmother', label_selector='app=test', verbose=False, timeout=300)
            except KeyboardInterrupt:
                pass

        assert call_count[0] == 3

    @patch('core.apps.api.management.commands.watch_k8s_events.time.sleep')
    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace',
           return_value='botmother')
    def test_watch_with_reconnect_on_410_error(
            self, mock_get_namespace, mock_apps_api_class, mock_load_config, mock_sleep):
        """Test that watcher reconnects immediately on 410 Gone error (resource version expired)"""
        from core.apps.api.management.commands.watch_k8s_events import Command

        mock_apps_api = MagicMock()
        mock_apps_api_class.return_value = mock_apps_api

        call_count = [0]

        def stream_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ApiException(status=410, reason="Gone")
            elif call_count[0] >= 2:
                raise KeyboardInterrupt()
            return iter([])

        mock_watch_instance = MagicMock()
        mock_watch_instance.stream.side_effect = stream_side_effect
        with patch('kubernetes.watch.Watch', return_value=mock_watch_instance):
            cmd = Command()
            try:
                cmd.handle(namespace='botmother', label_selector='app=test', verbose=False, timeout=300)
            except KeyboardInterrupt:
                pass

        assert call_count[0] >= 2
        assert mock_sleep.call_count == 0

    @patch('core.apps.api.management.commands.watch_k8s_events.time.sleep')
    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace',
           return_value='botmother')
    def test_watch_with_exponential_backoff(
            self, mock_get_namespace, mock_apps_api_class, mock_load_config, mock_sleep):
        """Test that watcher uses exponential backoff on errors"""
        from core.apps.api.management.commands.watch_k8s_events import Command

        mock_apps_api = MagicMock()
        mock_apps_api_class.return_value = mock_apps_api

        call_count = [0]

        def stream_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 4:
                raise KeyboardInterrupt()
            raise ApiException(status=500, reason="Internal Server Error")

        mock_watch_instance = MagicMock()
        mock_watch_instance.stream.side_effect = stream_side_effect
        with patch('kubernetes.watch.Watch', return_value=mock_watch_instance):
            cmd = Command()
            try:
                cmd.handle(namespace='botmother', label_selector='app=test', verbose=False, timeout=300)
            except KeyboardInterrupt:
                pass

        assert mock_sleep.call_count >= 3
        sleep_calls = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        assert sleep_calls[0] == 2
        assert sleep_calls[1] == 4
        assert sleep_calls[2] == 8

    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace',
           return_value='botmother')
    def test_process_event_updates_debug_status(
            self, mock_get_namespace, mock_apps_api_class, mock_load_config):
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
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace',
           return_value='botmother')
    def test_process_event_handles_pending_deployment(
            self, mock_get_namespace, mock_apps_api_class, mock_load_config):
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
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace',
           return_value='botmother')
    def test_process_event_handles_deleted_deployment(
            self, mock_get_namespace, mock_apps_api_class, mock_load_config):
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
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace',
           return_value='botmother')
    def test_process_event_ignores_deployments_without_engine_label(
            self, mock_get_namespace, mock_apps_api_class, mock_load_config):
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

    @patch('kubernetes.config.load_incluster_config')
    @patch('kubernetes.client.AppsV1Api')
    @patch('core.apps.api.management.commands.watch_k8s_events.get_namespace',
           return_value='botmother')
    def test_watch_stops_properly(
            self, mock_get_namespace, mock_apps_api_class, mock_load_config):
        """Test that watch is stopped properly even on errors"""
        from core.apps.api.management.commands.watch_k8s_events import Command

        mock_apps_api = MagicMock()
        mock_apps_api_class.return_value = mock_apps_api

        def stream_side_effect(*args, **kwargs):
            raise RuntimeError("Test error")

        mock_watch_instance = MagicMock()
        mock_watch_instance.stream.side_effect = stream_side_effect
        with patch('kubernetes.watch.Watch', return_value=mock_watch_instance):
            cmd = Command()
            try:
                cmd._watch_events('botmother', 'app=test', False, 300)
            except RuntimeError:
                pass

        mock_watch_instance.stop.assert_called_once()
