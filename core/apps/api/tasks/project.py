import logging
import celery

from core.apps.api.models.project import ProjectModel
from core.apps.api.models.resource import StorageResourceModel
from core.apps.api.services.resource import get_project_storage

logger = logging.getLogger(__name__)


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


@celery.shared_task(bind=True, max_retries=0)
def enable_default_modules(self, project_id: int):
    """Yangi loyiha uchun barcha active+is_default modullarni avtomatik yoqish.

    Best-effort: har modulni alohida try/except'ga o'rab ishlatamiz — bittasi
    yiqilsa qolganlar davom etadi. Idempotent: allaqachon enabled bo'lsa o'tkazib
    yuboriladi.
    """
    from core.apps.api.models.module import ModuleModel, ProjectModuleModel
    from core.apps.api.services.module_service import ManifestValidationError, deploy_module, fetch_manifest

    try:
        project = ProjectModel.objects.get(pk=project_id)
    except ProjectModel.DoesNotExist:
        logger.warning("enable_default_modules: project_id=%s topilmadi, o'tkazib yuborildi", project_id)
        return

    default_modules = ModuleModel.objects.filter(active=True, is_default=True)
    if not default_modules.exists():
        logger.info("enable_default_modules: default modullar yo'q, project_id=%s", project_id)
        return

    for module in default_modules:
        try:
            # Idempotentlik: allaqachon enabled bo'lsa o'tkazib yuboramiz
            if ProjectModuleModel.objects.filter(project=project, module=module, enabled=True).exists():
                logger.info(
                    "enable_default_modules: modul allaqachon yoqilgan slug=%s project_id=%s",
                    module.slug, project_id,
                )
                continue

            deploy_module(project, module)
            logger.info(
                "enable_default_modules: modul muvaffaqiyatli yoqildi slug=%s project_id=%s",
                module.slug, project_id,
            )

            try:
                fetch_manifest(module)
            except ManifestValidationError as exc:
                logger.warning(
                    "enable_default_modules: fetch_manifest muvaffaqiyatsiz slug=%s project_id=%s: %s",
                    module.slug, project_id, exc,
                )
        except Exception as exc:
            logger.error(
                "enable_default_modules: modul yoqishda xatolik slug=%s project_id=%s: %s",
                module.slug, project_id, exc,
            )
