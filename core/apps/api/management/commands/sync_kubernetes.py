# type: ignore
"""
Kubernetes events monitoring command.

This command monitors Kubernetes Pod events across ALL nodes in the cluster.
Unlike Docker Swarm, Kubernetes API provides cluster-wide event visibility
from a single connection point.

Usage:
    python manage.py sync_kubernetes

The command watches for Pod events and updates the status of debug/release
services in the database, then publishes WebSocket notifications.
"""
import logging
from typing import Any

from django.core.management.base import BaseCommand

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models.project import DebugModel, RelaseModel
from core.apps.websocket.services.events import ws_publish
from core.domain.ws import DebugContainerStatus, EventTypes, ReleaseContainerStatus

try:
    from kubernetes import client, config, watch
except ImportError:
    client = None
    config = None
    watch = None


logger = logging.getLogger(__name__)


def convert_k8s_status(phase: str, container_state: dict | None = None) -> str:
    """Convert Kubernetes Pod phase and container state to internal status.

    Args:
        phase: Pod phase (Pending, Running, Succeeded, Failed, Unknown)
        container_state: Container state dict with keys like 'running', 'waiting', 'terminated'

    Returns:
        Internal container status string
    """
    # Check container state first for more accurate status
    if container_state:
        if "running" in container_state:
            return ContainerStatusEnum.RUNNING.value
        elif "waiting" in container_state:
            reason = container_state["waiting"].get("reason", "")
            if reason in ("ContainerCreating", "PodInitializing"):
                return ContainerStatusEnum.INIT.value
            elif reason in ("CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"):
                return ContainerStatusEnum.FAILED.value
            return ContainerStatusEnum.PENDING.value
        elif "terminated" in container_state:
            exit_code = container_state["terminated"].get("exit_code", 0)
            if exit_code == 0:
                return ContainerStatusEnum.STOPPED.value
            return ContainerStatusEnum.FAILED.value

    # Fallback to Pod phase
    match phase:
        case "Pending":
            return ContainerStatusEnum.PENDING.value
        case "Running":
            return ContainerStatusEnum.RUNNING.value
        case "Succeeded":
            return ContainerStatusEnum.STOPPED.value
        case "Failed":
            return ContainerStatusEnum.FAILED.value
        case "Unknown":
            return ContainerStatusEnum.STOPPED.value
        case _:
            return ContainerStatusEnum.STOPPED.value


class Command(BaseCommand):
    help = "Monitor Kubernetes Pod events across all nodes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--namespace",
            type=str,
            default="default",
            help="Kubernetes namespace to watch (default: default)",
        )
        parser.add_argument(
            "--label-selector",
            type=str,
            default="",
            help="Label selector to filter pods (e.g., 'app=botmother')",
        )
        parser.add_argument(
            "--in-cluster",
            action="store_true",
            help="Use in-cluster Kubernetes configuration",
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        if client is None or config is None or watch is None:
            logger.critical("kubernetes package not installed. Run: pip install kubernetes")
            self.stderr.write(self.style.ERROR("kubernetes package not installed"))
            return

        namespace = options["namespace"]
        label_selector = options["label_selector"]
        in_cluster = options["in_cluster"]

        # Load Kubernetes configuration
        try:
            if in_cluster:
                config.load_incluster_config()
                logger.info("Using in-cluster Kubernetes configuration")
            else:
                config.load_kube_config()
                logger.info("Using kubeconfig file")
        except Exception as e:
            logger.critical(f"Failed to load Kubernetes configuration: {e}")
            self.stderr.write(self.style.ERROR(f"Failed to load Kubernetes configuration: {e}"))
            return

        v1 = client.CoreV1Api()
        w = watch.Watch()

        logger.info(f"Starting Kubernetes event watcher for namespace={namespace}")
        self.stdout.write(
            self.style.SUCCESS(f"Kubernetes event watcher started. Namespace: {namespace}")
        )

        try:
            # Watch for Pod events
            for event in w.stream(
                v1.list_namespaced_pod,
                namespace=namespace,
                label_selector=label_selector,
            ):
                try:
                    self._process_event(event)
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
        except KeyboardInterrupt:
            logger.info("Kubernetes event watcher stopped")
            self.stdout.write(self.style.WARNING("Kubernetes event watcher stopped"))
        finally:
            w.stop()

    def _process_event(self, event: dict) -> None:
        """Process a single Kubernetes Pod event.

        Args:
            event: Kubernetes watch event dict with 'type' and 'object' keys
        """
        event_type = event.get("type")  # ADDED, MODIFIED, DELETED
        pod = event.get("object")

        if pod is None:
            return

        pod_name = pod.metadata.name
        pod_labels = pod.metadata.labels or {}
        node_name = pod.spec.node_name or "unscheduled"
        phase = pod.status.phase

        # Get container state if available
        container_state = None
        if pod.status.container_statuses:
            container_state = pod.status.container_statuses[0].state.to_dict()

        # Determine service type from pod name or labels
        service_id = pod_labels.get("service-id") or pod_labels.get("app.kubernetes.io/instance")
        service_name = pod_labels.get("app") or pod_name

        if not service_id:
            # Try to extract from pod name (e.g., debug_123-abc or release_456-xyz)
            if pod_name.startswith("debug-") or pod_name.startswith("debug_"):
                service_type = "debug"
            elif pod_name.startswith("release-") or pod_name.startswith("release_"):
                service_type = "release"
            else:
                logger.debug(f"Skipping pod without service info: {pod_name}")
                return
        else:
            service_type = "debug" if "debug" in service_name.lower() else "release"

        # Convert status
        new_status = convert_k8s_status(phase, container_state)

        # Find and update service in database
        service = None
        try:
            if service_type == "debug":
                if service_id:
                    service = DebugModel.objects.get(service_id=service_id)
                else:
                    # Try to find by pod name pattern
                    logger.debug(f"Debug service not found by service_id, pod={pod_name}")
                    return
            else:
                if service_id:
                    service = RelaseModel.objects.get(service_id=service_id)
                else:
                    logger.debug(f"Release service not found by service_id, pod={pod_name}")
                    return
        except (DebugModel.DoesNotExist, RelaseModel.DoesNotExist):
            logger.info(
                f"{service_type} service not found in database: "
                f"service_id={service_id}, pod={pod_name}, node={node_name}"
            )
            return

        # Update service status
        old_status = service.status
        if old_status == new_status:
            return  # No change

        service.status = new_status
        service.save()

        logger.info(
            f"{service_type.capitalize()} status changed: "
            f"service={service.pk}, pod={pod_name}, "
            f"status={old_status}->{new_status}, "
            f"node={node_name}, event_type={event_type}"
        )

        # Send WebSocket notification
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
