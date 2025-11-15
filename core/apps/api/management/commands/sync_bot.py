from django.core.management import BaseCommand
from typing import Any

from core.apps.api.services.bot import TelegramBotService
from core.apps.api.tasks.bot import sync_bot


class Command(BaseCommand):

    def handle(self, *args: Any, **options: Any) -> str | None:
        sync_bot()
