from typing import Any

from django.core.management import BaseCommand

from core.apps.payment.tasks.payment import process_resource_usage


class Command(BaseCommand):
    help = "Run the (placeholder) resource-usage payment task manually."

    def handle(self, *args: Any, **options: Any) -> str | None:
        process_resource_usage()
        return None
