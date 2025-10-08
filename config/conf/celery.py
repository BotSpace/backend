from datetime import timedelta

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "sync_debug_services": {
        "task": "core.apps.api.tasks.docker_task.sync_debug_service_status",
        "schedule": crontab(minute="*/1"),
    },
    "sync_fast_debug_services": {
        "task": "core.apps.api.tasks.docker_task.sync_fast_debug_service_status",
        "schedule": timedelta(seconds=5),
    },
    "sync_relase_services": {
        "task": "core.apps.api.tasks.docker_task.sync_release_service_status",
        "schedule": crontab(minute="*/1"),
    },
    "sync_fast_relase_services": {
        "task": "core.apps.api.tasks.docker_task.sync_fast_release_service_status",
        "schedule": timedelta(seconds=5),
    },
}
