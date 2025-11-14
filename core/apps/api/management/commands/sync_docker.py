# type: ignore
from typing import Any
from core.apps.api.models.project import DebugModel, RelaseModel
from core.apps.api.services.docker_service import client, convert_status, get_service_status
import logging

from django.core.management.base import BaseCommand

from core.apps.websocket.services.events import ws_publish
from core.domain.ws import DebugContainerStatus, EventTypes, ReleaseContainerStatus


class Command(BaseCommand):

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            for event in client.events(decode=True):
                try:
                    if event.get("Type") != "container":
                        logging.info("invalid event event=%s", event.get("Type"))
                        continue
                    attr = event.get("Actor", {}).get("Attributes", {})
                    service_id = attr.get("com.docker.swarm.service.id", None)
                    if service_id is None:
                        logging.warning("service id not found")
                        continue
                    status = event.get("status", None)
                    if status is None:
                        logging.info("status not found event=%s", event)
                        continue
                    name = attr.get("com.docker.swarm.service.name", None)
                    if name is None:
                        logging.info("name not found")
                        continue
                    service_type = "debug" if name.startswith("debug") else "release"
                    service = None
                    if service_type == "debug":
                        try:
                            service = DebugModel.objects.get(service_id=service_id)
                        except DebugModel.DoesNotExist:
                            logging.info(
                                "debug model instance not found service=%s event=%s status=%s",
                                service_id,
                                event.get("Type"),
                                status,
                            )
                            continue
                    elif service_type == "release":
                        try:
                            service = RelaseModel.objects.get(service_id=service_id)
                        except DebugModel.DoesNotExist:
                            logging.info(
                                "release model instance not found service=%s event=%s status=%s",
                                service_id,
                                event.get("Type"),
                                status,
                            )
                            continue
                    if service is None:
                        logging.info("invalid service")
                        continue
                    service.status = convert_status(status)
                    service.save()
                    if service_type == "debug":
                        logging.info("debug status change status=%s service=%s", status, service.pk)
                        ws_publish(
                            service.project.owner.id,
                            DebugContainerStatus(project=service.project.id, status=service.status),
                            EventTypes.DEBUG_STATUS,
                        )
                    if service_type == "release":
                        logging.info("release status change status=%s service=%s", status, service.pk)
                        ws_publish(
                            service.project.owner.id,
                            ReleaseContainerStatus(
                                project=service.project.id, status=service.status, version=service.version
                            ),
                            EventTypes.RELEASE_STATUS,
                        )
                except Exception as e:
                    logging.error("sync docker error=%s", e)

        except KeyboardInterrupt:
            logging.info("docker kuzatuvchi to'xtatildi")
