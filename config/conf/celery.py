from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "sync_bot": {
        "task": "core.apps.api.tasks.bot.sync_bot",
        "schedule": crontab(hour="*/1", minute="0"),
    },
    # "sync_storage": {
    #     "task": "core.apps.api.tasks.project.sync_storage",
    #     "schedule": crontab(minute="*/10"),
    # },
    "sync_debug": {
        "task": "core.apps.api.tasks.debug.sync_debug",
        "schedule": crontab(minute="*/5"),
    },
    # "process_resource_usage": {
    #     "task": "payment.process_resource_usage",
    #     "schedule": crontab(minute="0", hour="*/1"),
    # },
    # Har 5 daqiqada — qisqa TTL (soniya/daqiqa) fayllar uzoq qolib ketmasligi uchun.
    # Aniq soniyada o'chmaydi (davriy supurish), eng ko'pi bilan ~5 daqiqa kechikadi.
    "cleanup_expired_files": {
        "task": "core.apps.api.tasks.file.cleanup_expired_files",
        "schedule": crontab(minute="*/5"),
    },
    # Har 10 daqiqada — CrashLoopBackOff/Error holatidagi release deployment'larni
    # Kubernetes'dan o'chiradi, DB'da RelaseModel record FAILED statusida qoladi.
    "cleanup_failed_releases": {
        "task": "core.apps.api.tasks.release.cleanup_failed_releases",
        "schedule": crontab(minute="*/10"),
    },
    # Har soatda har loyihaning disk hajmini snapshot qiladi (monitoring tarix charti).
    "snapshot_project_disk": {
        "task": "core.apps.api.tasks.monitoring.snapshot_project_disk",
        "schedule": crontab(minute="0"),
    },
}
