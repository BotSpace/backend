import celery

from core.apps.api.models.project import ProjectModel
from core.apps.api.models.resource import StorageResourceModel
from core.apps.api.services.resource import get_project_storage


@celery.shared_task
def sync_storage():
    for project in ProjectModel.objects.all():
        StorageResourceModel.objects.create(project=project, storage=get_project_storage(project))
