# type: ignore
"""
Kubernetes pod event watcher management command.

This command watches for Kubernetes pod events from ALL nodes in the cluster
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
    get_k8s_client,
    get_namespace,
    convert_k8s_event_status,
)
import logging

from django.core.management.base import BaseCommand
from kubernetes import watch

from core.apps.websocket.services.events import ws_publish
from core.domain.ws import DebugContainerStatus, EventTypes, ReleaseContainerStatus


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Watch Kubernetes pod events for engine status updates. "
        "Receives events from ALL nodes in the cluster automatically."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--namespace',
            type=str,
            default=None,
            help='Kubernetes namespace to watch (default: from K8S_NAMESPACE env var)',
        )
        parser.add_argument(
            '--label-selector',
            type=str,
            default='app=botmother-engine',
            help='Label selector for filtering pods (default: app=botmother-engine)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging of all events',
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        namespace = options.get('namespace') or get_namespace()
        label_selector = options.get('label_selector')
        verbose = options.get('verbose', False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting Kubernetes pod event watcher\n"
                f"  Namespace: {namespace}\n"
                f"  Label selector: {label_selector}\n"
                f"  Note: Events from ALL nodes are received automatically"
            )
        )

        try:
            api = get_k8s_client()
            w = watch.Watch()

            logger.info(
                f"Kubernetes event watcher started - namespace={namespace}, "
                f"label_selector={label_selector}"
            )

            for event in w.stream(
                api.list_namespaced_pod,
                namespace=namespace,
                label_selector=label_selector,
            ):
                try:
                    self._process_event(event, verbose)
                except Exception as e:
                    logger.error(f"Error processing pod event: {e}")

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nKubernetes pod watcher stopped"))
            logger.info("Kubernetes pod watcher stopped by user")
        except Exception as e:
            logger.error(f"Kubernetes watcher error: {e}")
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            raise

    def _process_event(self, event: dict, verbose: bool) -> None:
        """Process a single Kubernetes pod event"""
        event_type = event.get("type")
        pod = event.get("object")

        if not pod or not event_type:
            return

        pod_name = pod.metadata.name
        labels = pod.metadata.labels or {}
        engine_name = labels.get("engine-name")
        node_name = pod.spec.node_name if pod.spec else "unassigned"

        if not engine_name:
            if verbose:
                logger.debug(f"Skipping pod without engine-name label: {pod_name}")
            return

        # Get status from pod
        phase = pod.status.phase if pod.status else "Unknown"
        reason = phase

        if pod.status and pod.status.container_statuses:
            container_state = pod.status.container_statuses[0].state
            if container_state.running:
                reason = "running"
            elif container_state.waiting:
                reason = container_state.waiting.reason or "waiting"
            elif container_state.terminated:
                reason = container_state.terminated.reason or "terminated"

        # Determine service type from engine name prefix
        service_type = "debug" if engine_name.startswith("debug") else "release"

        # Find and update service in database
        service = None
        try:
            if service_type == "debug":
                service = DebugModel.objects.get(service_id=pod_name)
            else:
                service = RelaseModel.objects.get(service_id=pod_name)
        except (DebugModel.DoesNotExist, RelaseModel.DoesNotExist):
            if verbose:
                logger.info(
                    f"{service_type} service not found in database: "
                    f"pod_name={pod_name}, engine_name={engine_name}, node={node_name}"
                )
            return

        # Update service status
        old_status = service.status
        new_status = convert_k8s_event_status(event_type, reason)
        
        if old_status != new_status:
            service.status = new_status
            service.save(update_fields=['status', 'updated_at'])

            logger.info(
                f"{service_type.upper()} status change: pod={pod_name}, node={node_name}, "
                f"status={old_status}->{new_status}, event={event_type}, reason={reason}"
            )

            # Send WebSocket notification
            self._send_ws_notification(service, service_type)
        elif verbose:
            logger.debug(
                f"{service_type} event (no status change): pod={pod_name}, "
                f"node={node_name}, status={new_status}, event={event_type}"
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
