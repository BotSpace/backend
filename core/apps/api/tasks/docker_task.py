from celery import shared_task
from core.apps.websocket.services import ws_publish

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models.project import DebugModel, RelaseModel
from core.apps.api.services import get_service_status
from core.domain.ws import DebugContainerStatus, EventTypes


@shared_task
def sync_debug_service_status():
    services = DebugModel.objects.filter(service_id__isnull=False).all()
    for service in services:
        try:
            service.status = get_service_status(service.service_id)
            service.save()
        except Exception as e:
            print(e)


@shared_task
def sync_fast_debug_service_status():
    services = DebugModel.objects.filter(
        service_id__isnull=False, status__in=[ContainerStatusEnum.INIT.value, ContainerStatusEnum.STOPPING.value]
    ).all()
    for service in services:
        try:
            service.status = get_service_status(service.service_id)
            service.save()
        except Exception as e:
            print(e)


@shared_task
def sync_release_service_status():
    services = RelaseModel.objects.filter(service_id__isnull=False).all()
    for service in services:
        try:
            service.status = get_service_status(service.service_id)
            service.save()
            ws_publish(
                service.project.owner.id,
                DebugContainerStatus(project=service.project.id, status=service.status),
                EventTypes.RELEASE_CONTAINER_STATUS,
            )
        except Exception as e:
            print(e)


@shared_task
def sync_fast_release_service_status():
    services = RelaseModel.objects.filter(
        service_id__isnull=False, status__in=[ContainerStatusEnum.INIT.value, ContainerStatusEnum.STOPPING.value]
    ).all()
    for service in services:
        try:
            service.status = get_service_status(service.service_id)
            service.save()
            ws_publish(
                service.project.owner.id,
                DebugContainerStatus(project=service.project.id, status=service.status),
                EventTypes.RELEASE_CONTAINER_STATUS,
            )
        except Exception as e:
            print(e)
