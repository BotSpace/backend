# type: ignore
"""
Kubernetes event webhook handlers for engine pod status updates.
"""
import logging
from typing import Any

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.apps.api.models.project import DebugModel, RelaseModel
from core.apps.api.services.kubernetes_service import convert_k8s_event_status
from core.apps.websocket.services.events import ws_publish
from core.domain.ws import DebugContainerStatus, EventTypes, ReleaseContainerStatus


logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])  # TODO: Add API key authentication
def kubernetes_event_webhook(request) -> Response:
    """
    Receive Kubernetes events from a k8s event watcher service.
    
    Expected payload:
    {
        "type": "ADDED" | "MODIFIED" | "DELETED",
        "object": {
            "metadata": {
                "name": "pod_name",
                "namespace": "namespace",
                "labels": {
                    "app": "botmother-engine",
                    "engine-name": "debug-123",
                    "project_id": "123"
                }
            },
            "status": {
                "phase": "Running" | "Pending" | "Succeeded" | "Failed" | "Unknown",
                "containerStatuses": [
                    {
                        "state": {
                            "running": {},
                            "waiting": {"reason": "ContainerCreating"},
                            "terminated": {"reason": "Completed", "exitCode": 0}
                        }
                    }
                ]
            }
        },
        "node_name": "node_name"
    }
    """
    try:
        data = request.data
        
        event_type = data.get("type")
        if not event_type:
            logger.warning("Missing event type in Kubernetes event")
            return Response(
                {"status": "error", "reason": "missing event type"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        obj = data.get("object", {})
        metadata = obj.get("metadata", {})
        labels = metadata.get("labels", {})
        pod_status = obj.get("status", {})
        
        # Check if this is a botmother engine pod
        if labels.get("app") != "botmother-engine":
            logger.debug("Skipping non-engine pod event")
            return Response({"status": "ignored", "reason": "not a botmother engine pod"})
        
        pod_name = metadata.get("name")
        engine_name = labels.get("engine-name")
        
        if not pod_name or not engine_name:
            logger.debug("Missing pod name or engine name")
            return Response({"status": "ignored", "reason": "missing pod/engine name"})
        
        # Get status from pod phase or container status
        phase = pod_status.get("phase", "Unknown")
        container_statuses = pod_status.get("containerStatuses", [])
        
        # Determine the reason/status
        reason = phase
        if container_statuses:
            container_state = container_statuses[0].get("state", {})
            if "running" in container_state:
                reason = "running"
            elif "waiting" in container_state:
                reason = container_state["waiting"].get("reason", "waiting")
            elif "terminated" in container_state:
                reason = container_state["terminated"].get("reason", "terminated")
        
        # Get node information
        node_name = data.get("node_name", obj.get("spec", {}).get("nodeName", "unknown"))
        
        # Determine service type from engine name
        service_type = "debug" if engine_name.startswith("debug") else "release"
        
        # Find and update service - pod_name is used as service_id for k8s
        service = None
        try:
            if service_type == "debug":
                service = DebugModel.objects.get(service_id=pod_name)
            else:
                service = RelaseModel.objects.get(service_id=pod_name)
        except (DebugModel.DoesNotExist, RelaseModel.DoesNotExist):
            logger.info(
                f"{service_type} service not found: pod_name={pod_name}, "
                f"engine_name={engine_name}, node={node_name}"
            )
            return Response({"status": "ignored", "reason": "service not found in database"})
        
        # Update service status
        old_status = service.status
        new_status = convert_k8s_event_status(event_type, reason)
        service.status = new_status
        service.save()
        
        logger.info(
            f"{service_type.capitalize()} status changed: "
            f"service={service.pk}, pod={pod_name}, "
            f"status={old_status}->{new_status}, "
            f"node={node_name}, event={event_type}, reason={reason}"
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
        
        return Response({
            "status": "success",
            "service_type": service_type,
            "pod_name": pod_name,
            "old_status": old_status,
            "new_status": new_status,
            "node": node_name,
        })
        
    except Exception as e:
        logger.error(f"Error processing Kubernetes event: {e}", exc_info=True)
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
