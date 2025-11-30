import logging
import celery

from core.apps.api.models.project import ProjectModel
from core.apps.api.models.resource import StorageResourceModel
from core.apps.api.services.resource import get_project_storage


@celery.shared_task
def sync_storage():
    for project in ProjectModel.objects.all():
        try:
            storage = get_project_storage(project)
            if storage is None:
                storage = 0
            StorageResourceModel.objects.create(project=project, storage=storage)
        except Exception as err:
            logging.info("sync storage err=%s", err)
