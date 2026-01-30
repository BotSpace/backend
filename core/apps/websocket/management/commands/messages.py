from django.core.management.base import BaseCommand
from core.services.redis_service import subscribe


class Command(BaseCommand):

    def handle(self, *args, **options):
        for event in subscribe("websocket"):
            print(event)
        pass
