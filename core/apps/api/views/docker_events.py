# type: ignore
import logging
from typing import Any

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.apps.api.models.project import DebugModel, RelaseModel
from core.apps.api.services.docker_service import convert_status
from core.apps.websocket.services.events import ws_publish
from core.domain.ws import DebugContainerStatus, EventTypes, ReleaseContainerStatus


logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])  # TODO: Add API key authentication
def docker_event_webhook(request) -> Response:
    """
    Receive Docker events from docker-event-forwarder service running on each node.
    
    Expected payload:
    {
        "Type": "container",
        "Action": "start",
        "status": "start",
        "Actor": {
            "ID": "container_id",
            "Attributes": {
                "com.docker.swarm.service.id": "service_id",
                "com.docker.swarm.service.name": "service_name"
            }
        },
        "time": 1234567890,
        "timeNano": 1234567890000000000,
        "node_id": "node_id",
        "node_name": "node_name"
    }
    """
    try:
        data = request.data
        
        # Validate event type
        if data.get("Type") != "container":
            logger.debug(f"Skipping non-container event: {data.get('Type')}")
            return Response({"status": "ignored", "reason": "not a container event"})
        
        # Get service information
        actor = data.get("Actor", {})
        attributes = actor.get("Attributes", {})
        service_id = attributes.get("com.docker.swarm.service.id")
        service_name = attributes.get("com.docker.swarm.service.name")
        
        if not service_id or not service_name:
            logger.debug("Event doesn't have service ID or name, skipping")
            return Response({"status": "ignored", "reason": "not a service container"})
        
        # Get status
        event_status = data.get("status") or data.get("Action")
        if not event_status:
            logger.warning(f"No status or action in event: {data}")
            return Response({"status": "error", "reason": "missing status"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get node information
        node_id = data.get("node_id", "unknown")
        node_name = data.get("node_name", "unknown")
        
        # Determine service type
        service_type = "debug" if service_name.startswith("debug") else "release"
        
        # Find and update service
        service = None
        try:
            if service_type == "debug":
                service = DebugModel.objects.get(service_id=service_id)
            else:
                service = RelaseModel.objects.get(service_id=service_id)
        except (DebugModel.DoesNotExist, RelaseModel.DoesNotExist):
            logger.info(
                f"{service_type} service not found: service_id={service_id}, "
                f"name={service_name}, node={node_name}"
            )
            return Response({"status": "ignored", "reason": "service not found in database"})
        
        # Update service status
        old_status = service.status
        new_status = convert_status(event_status)
        service.status = new_status
        service.save()
        
        logger.info(
            f"{service_type.capitalize()} status changed: "
            f"service={service.pk}, name={service_name}, "
            f"status={old_status}->{new_status}, "
            f"node={node_name}, event={event_status}"
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
            "service_id": service_id,
            "old_status": old_status,
            "new_status": new_status,
            "node": node_name,
        })
        
    except Exception as e:
        logger.error(f"Error processing Docker event: {e}", exc_info=True)
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
