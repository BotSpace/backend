from django.core.management.base import BaseCommand

from core.apps.api.models.message import MessageModel
from core.apps.api.tasks import send_message


class Command(BaseCommand):
    help = "send message"

    def handle(self, *args, **options):
        send_message(19)