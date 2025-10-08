from datetime import timedelta

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "sync_services": {
        "task": "core.apps.api.tasks.docker_task.sync_debug_service_status",
        "schedule": crontab(minute="*/1"),
    },
    "sync_starting_services": {
        "task": "core.apps.api.tasks.docker_task.sync_starting_debug_service_status",
        "schedule": timedelta(seconds=5),
    },
}
