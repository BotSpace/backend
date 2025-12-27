import logging
from celery import shared_task
from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models.project import DebugModel
from django.utils import timezone
from datetime import timedelta
from core.apps.api.services.docker_service import remove_service


@shared_task
def sync_debug():
    last_time = timezone.now() - timedelta(minutes=30)
    containers = DebugModel.objects.filter(
        project__is_template=False,
        status=ContainerStatusEnum.RUNNING.value,
        updated_at__lte=last_time,
    )
    for container in containers:
        try:
            remove_service(container.service_id)
            container.status = ContainerStatusEnum.STOPPING.value
            container.save()
        except Exception as err:
            logging.error(err)
