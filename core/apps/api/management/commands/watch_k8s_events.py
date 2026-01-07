"""
Kubernetes deployment event watcher management command.

This command watches for Kubernetes deployment events from ALL nodes in the cluster
and updates the database accordingly. The Kubernetes API automatically aggregates
events from all nodes, so a single watcher is sufficient for the entire cluster.

Usage:
    python manage.py watch_k8s_events

Note: For production deployment, this command should run as a single instance
(e.g., Kubernetes Deployment with replicas=1) to avoid duplicate event processing.
"""

from typing import Any
from core.apps.api.models.project import DebugModel, RelaseModel
from core.apps.api.services.kubernetes_service import (
    get_namespace,
    convert_k8s_event_status,
)
import logging
import time

from django.core.management.base import BaseCommand
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

from core.apps.websocket.services.events import ws_publish
from core.domain.ws import DebugContainerStatus, EventTypes, ReleaseContainerStatus


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Watch Kubernetes deployment events for engine status updates. "
        "Receives events from ALL nodes in the cluster automatically."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--namespace",
            type=str,
            default=None,
            help="Kubernetes namespace to watch (default: from K8S_NAMESPACE env var)",
        )
        parser.add_argument(
            "--label-selector",
            type=str,
            default="app=botmother-engine",
            help="Label selector for filtering deployments (default: app=botmother-engine)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose logging of all events",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=300,
            help="Watch stream timeout in seconds (default: 300). Stream will reconnect after timeout.",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        namespace = options.get("namespace") or get_namespace()
        label_selector = options.get("label_selector")
        verbose = options.get("verbose", False)
        timeout = options.get("timeout", 300)

        print(
            f"Starting Kubernetes deployment event watcher\n"
            f"  Namespace: {namespace}\n"
            f"  Label selector: {label_selector}\n"
            f"  Watch timeout: {timeout}s (will auto-reconnect)\n"
            f"  Note: Events from ALL nodes are received automatically"
        )

        try:
            # Load Kubernetes config
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes config")
            except config.ConfigException:
                config.load_kube_config()
                logger.info("Loaded kubeconfig file")

            # Run watcher with automatic reconnection
            self._watch_with_reconnect(namespace, label_selector, verbose, timeout)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nKubernetes deployment watcher stopped"))
            logger.info("Kubernetes deployment watcher stopped by user")

    def _watch_with_reconnect(self, namespace: str, label_selector: str, verbose: bool, timeout: int) -> None:
        """Watch events with automatic reconnection on failures"""
        retry_count = 0
        max_backoff = 60  # Maximum backoff time in seconds

        while True:
            try:
                # Calculate exponential backoff: 2^retry_count seconds, capped at max_backoff
                if retry_count > 0:
                    backoff = min(2 ** retry_count, max_backoff)
                    logger.info(f"Reconnecting in {backoff} seconds... (attempt {retry_count + 1})")
                    time.sleep(backoff)

                # Reset retry count on successful connection
                logger.info(
                    f"Kubernetes deployment event watcher started - namespace={namespace}, "
                    f"label_selector={label_selector}, timeout={timeout}s"
                )

                self._watch_events(namespace, label_selector, verbose, timeout)

                # If we get here, the watch ended normally (not an error)
                # Reset retry count
                retry_count = 0
                logger.info("Watch stream ended normally, reconnecting...")

            except ApiException as e:
                retry_count += 1
                if e.status == 410:
                    # 410 Gone - resource version is too old
                    logger.warning("Resource version expired (410 Gone), reconnecting immediately...")
                    retry_count = 0  # Don't backoff for resource version issues
                else:
                    logger.error(f"Kubernetes API error (attempt {retry_count}): {e.status} - {e.reason}")

            except Exception as e:
                retry_count += 1
                logger.error(f"Kubernetes watcher error (attempt {retry_count}): {e}")

    def _watch_events(self, namespace: str, label_selector: str, verbose: bool, timeout: int) -> None:
        """Watch events from Kubernetes API with timeout"""
        apps_api = client.AppsV1Api()
        w = watch.Watch()

        try:
            for event in w.stream(
                apps_api.list_namespaced_deployment,
                namespace=namespace,
                label_selector=label_selector,
                timeout_seconds=timeout,
            ):
                try:
                    self._process_event(event, verbose)
                except Exception as e:
                    logger.error(f"Error processing deployment event: {e}")
        finally:
            # Ensure watch is stopped properly
            w.stop()

    def _process_event(self, event: dict, verbose: bool) -> None:
        """Process a single Kubernetes deployment event"""
        event_type = event.get("type")
        deployment = event.get("object")

        if not deployment or not event_type:
            return

        # Validate deployment metadata exists
        if not deployment.metadata or not deployment.metadata.name:
            if verbose:
                logger.debug("Skipping deployment event with missing metadata")
            return

        deployment_name = deployment.metadata.name
        labels = deployment.metadata.labels or {}
        engine_name = labels.get("engine-name")

        if not engine_name:
            if verbose:
                logger.debug(f"Skipping deployment without engine-name label: {deployment_name}")
            return

        # Get status from deployment
        status = deployment.status
        ready_replicas = status.ready_replicas if status else 0
        replicas = status.replicas if status else 0

        # Determine the reason/status
        if ready_replicas and ready_replicas > 0:
            reason = "running"
        elif replicas and replicas > 0:
            reason = "pending"
        else:
            reason = "stopped"

        # Determine service type from engine name prefix
        service_type = "debug" if engine_name.startswith("debug") else "release"

        # Find and update service in database
        service = None
        try:
            if service_type == "debug":
                service = DebugModel.objects.get(service_id=deployment_name)
            else:
                service = RelaseModel.objects.get(service_id=deployment_name)
        except (DebugModel.DoesNotExist, RelaseModel.DoesNotExist):
            if verbose:
                logger.info(
                    f"{service_type} service not found in database: "
                    f"deployment_name={deployment_name}, engine_name={engine_name}"
                )
            return

        # Update service status
        old_status = service.status
        new_status = convert_k8s_event_status(event_type, reason)

        if old_status != new_status:
            service.status = new_status
            service.save(update_fields=["status", "updated_at"])

            logger.info(
                f"{service_type.upper()} status change: deployment={deployment_name}, "
                f"status={old_status}->{new_status}, event={event_type}, reason={reason}, "
                f"replicas={replicas}, ready={ready_replicas}"
            )

            # Send WebSocket notification
            self._send_ws_notification(service, service_type)
        elif verbose:
            logger.debug(
                f"{service_type} event (no status change): deployment={deployment_name}, "
                f"status={new_status}, event={event_type}, replicas={replicas}, ready={ready_replicas}"
            )

    def _send_ws_notification(self, service, service_type: str) -> None:
        """Send WebSocket notification for status change"""
        try:
            if service_type == "debug":
                ws_publish(
                    service.project.owner.id,
                    DebugContainerStatus(
                        project=service.project.id,
                        status=service.status,
                        service_id=service.service_id,
                        updated_at=service.updated_at.isoformat(),
                    ),
                    EventTypes.DEBUG_STATUS,
                )
            else:
                ws_publish(
                    service.project.owner.id,
                    ReleaseContainerStatus(
                        project=service.project.id,
                        status=service.status,
                        version=service.version,
                        service_id=service.service_id,
                    ),
                    EventTypes.RELEASE_STATUS,
                )
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")
