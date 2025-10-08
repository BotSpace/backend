from django.core import management

from ... import handlers
from .base import bot


class Command(management.BaseCommand):
    def handle(self, *args, **options):
        try:
            bot.register_message_handler(commands=["start"], callback=handlers.start_handler)
            bot.register_message_handler(content_types=["contact"], callback=handlers.phone_handler)
            bot.polling()
            print("Bot Command")
        except Exception as e:
            print("bot ishga tushmadi: ", e)
