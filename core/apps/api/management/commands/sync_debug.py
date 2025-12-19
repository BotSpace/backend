from django.core.management import BaseCommand
from typing import Any

from core.apps.api.tasks.debug import sync_debug


class Command(BaseCommand):

    def handle(self, *args: Any, **options: Any) -> str | None:
        sync_debug()
