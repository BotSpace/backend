import logging

import celery
from django.utils import timezone

from core.apps.api.models.file import FileModel

logger = logging.getLogger(__name__)


@celery.shared_task
def cleanup_expired_files():
    """Muddati o'tgan fayllarni storage va DB'dan o'chiradi."""
    expired_qs = FileModel.objects.filter(expires_at__lt=timezone.now())
    count = 0
    for obj in expired_qs.iterator():
        try:
            obj.file.delete(save=False)
            obj.delete()
            count += 1
        except Exception as err:
            logger.error("cleanup_expired_files: pk=%s err=%s", obj.pk, err)
    logger.info("cleanup_expired_files: deleted=%d", count)
    return count
