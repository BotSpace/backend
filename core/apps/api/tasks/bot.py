import logging
from celery import shared_task

from core.apps.api.exceptions.bot import ReleaseBotTokenNotFound
from core.apps.api.models.project import ProjectModel
from core.apps.api.services.bot import TelegramBotService
import time


@shared_task
def sync_bot():
    projects = ProjectModel.objects.all()
    service = TelegramBotService()
    for project in projects:
        time.sleep(0.5)
        try:
            service.set_project(project)
            service.update_me_photo()
            service.update_username()
            service.save()
        except ReleaseBotTokenNotFound:
            pass
        except Exception as e:
            logging.error("sync bot error project=%s error=%s", project, e)
