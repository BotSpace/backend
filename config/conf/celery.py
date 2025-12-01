from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "sync_bot": {
        "task": "core.apps.api.tasks.bot.sync_bot",
        "schedule": crontab(hour="*/1", minute="0"),
    },
    "sync_storage": {
        "task": "core.apps.api.tasks.project.sync_storage",
        "schedule": crontab(minute="*/10"),
    },
    # "proccess_payment": {
    #     "task": "core.apps.payment.tasks.payment.proccess_payment",
    #     "schedule": crontab(minute="0", hour="*/1"),
    # },
    "monitor_plan_limits": {
        "task": "monitor_plan_limits",
        "schedule": crontab(minute="0", hour="*/6"),  # Every 6 hours
    },
}
