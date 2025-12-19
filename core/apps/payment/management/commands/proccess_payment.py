from django.core.management import BaseCommand
from typing import Any

from core.apps.payment.tasks.payment import proccess_payment


class Command(BaseCommand):

    def handle(self, *args: Any, **options: Any) -> str | None:
        proccess_payment()
