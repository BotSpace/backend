import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def snapshot_project_disk():
    """Har loyihaning disk hajmini snapshot jadvaliga yozadi (tarix charti uchun)."""
    from core.apps.api.services.monitoring import snapshot_all_projects_disk

    count = snapshot_all_projects_disk()
    logger.info("snapshot_project_disk: wrote=%d", count)
    return count
