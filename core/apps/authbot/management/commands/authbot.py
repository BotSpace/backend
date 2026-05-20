import logging

from django.core import management

from ... import handlers
from .base import bot

logger = logging.getLogger(__name__)


class Command(management.BaseCommand):
    def handle(self, *args, **options):
        if bot is None:
            self.stderr.write(self.style.ERROR("BOT_TOKEN not configured"))
            return
        try:
            bot.register_message_handler(commands=["start"], callback=handlers.start_handler)
            bot.register_message_handler(content_types=["contact"], callback=handlers.phone_handler)
            self.stdout.write(self.style.SUCCESS("Bot ishga tushdi, polling boshlandi"))
            bot.polling()
        except Exception:
            logger.exception("Bot polling failed")
            self.stderr.write(self.style.ERROR("bot ishga tushmadi"))
