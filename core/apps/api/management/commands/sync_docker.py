from typing import Any

from django.core.management.base import BaseCommand

from core.apps.api.tasks import sync_debug_service_status


class Command(BaseCommand):

    def handle(self, *args: Any, **options: Any) -> str | None:
        sync_debug_service_status()
