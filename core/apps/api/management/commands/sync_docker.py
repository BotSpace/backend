# type: ignore
"""
Kubernetes pod event watcher management command.

This command watches for Kubernetes pod events and updates the database accordingly.
For production use, consider using a separate k8s-event-watcher service that sends
events via webhook to /api/kubernetes/events/ endpoint.
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


class Command(BaseCommand):
    help = "Watch Kubernetes pod events for engine status updates"

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            api = get_k8s_client()
            namespace = get_namespace()
            w = watch.Watch()
            
            logging.info(f"Starting Kubernetes pod watcher in namespace: {namespace}")
            
            for event in w.stream(
                api.list_namespaced_pod,
                namespace=namespace,
                label_selector="app=botmother-engine",
            ):
                try:
                    event_type = event.get("type")
                    pod = event.get("object")
                    
                    if not pod or not event_type:
                        continue
                    
                    pod_name = pod.metadata.name
                    labels = pod.metadata.labels or {}
                    engine_name = labels.get("engine-name")
                    
                    if not engine_name:
                        continue
                    
                    # Get status
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
                    
                    # Determine service type
                    service_type = "debug" if engine_name.startswith("debug") else "release"
                    
                    # Find and update service
                    service = None
                    try:
                        if service_type == "debug":
                            service = DebugModel.objects.get(service_id=pod_name)
                        else:
                            service = RelaseModel.objects.get(service_id=pod_name)
                    except (DebugModel.DoesNotExist, RelaseModel.DoesNotExist):
                        logging.info(
                            f"{service_type} service not found: pod_name={pod_name}, "
                            f"engine_name={engine_name}"
                        )
                        continue
                    
                    # Update status
                    new_status = convert_k8s_event_status(event_type, reason)
                    service.status = new_status
                    service.save()
                    
                    logging.info(
                        f"{service_type} status change: pod={pod_name}, "
                        f"status={new_status}, event={event_type}, reason={reason}"
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
                        
                except Exception as e:
                    logging.error(f"Error processing pod event: {e}")
                    
        except KeyboardInterrupt:
            logging.info("Kubernetes pod watcher stopped")
