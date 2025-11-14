from typing import Any
from core.apps.api.models.project import DebugModel, RelaseModel
from core.apps.api.services.docker_service import client
import logging

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args: Any, **options: Any) -> str | None:
        try:
            for event in client.events(decode=True):
                if event.get("Type") != "container":
                    continue
                attr = event.get("Actor", {}).get("Attributes", {})
                service_id = attr.get("com.docker.swarm.service.id", None)
                if service_id is None:
                    continue
                status = event.get("status", None)
                if status is None:
                    continue
                name = attr.get("com.docker.swarm.service.name", None)
                if name is None:
                    continue
                service_type = "debug" if name.startswith("debug") else "release"
                service = None
                if service_type == "debug":
                    try:
                        service = DebugModel.objects.get(service_id=service_id)
                    except DebugModel.DoesNotExist:
                        continue
                elif service_type == "release":
                    try:
                        service = RelaseModel.objects.get(service_id=service_id)
                    except DebugModel.DoesNotExist:
                        continue
                if service is None:
                    continue
                print(service, status)

        except KeyboardInterrupt:
            logging.info("docker kuzatuvchi to'xtatildi")
