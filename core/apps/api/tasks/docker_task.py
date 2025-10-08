from celery import shared_task

from core.apps.api.models.project import DebugModel
from core.apps.api.services import get_service_status


@shared_task
def sync_debug_service_status():
    services = DebugModel.objects.filter(service_id__isnull=False).all()
    for service in services:
        try:
            service.status = get_service_status(service.service_id)
            service.save()
        except Exception as e:
            print(e)
