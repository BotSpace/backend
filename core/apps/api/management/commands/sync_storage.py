from django.core.management import BaseCommand
from typing import Any

from core.apps.api.tasks.project import sync_storage


class Command(BaseCommand):

    def handle(self, *args: Any, **options: Any) -> str | None:
        sync_storage()
