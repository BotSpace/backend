from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "test": {
        "task": "core.apps.api.tasks.docker_task.sync_debug_service_status",
        "schedule": crontab(minute="*/2"),
    },
}
