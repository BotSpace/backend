import logging

from ..models import BotUser
from ..management.commands.base import bot
from ....http.models import SmsConfirm

logger = logging.getLogger(__name__)


class BotService:

    def __init__(self) -> None: ...

    def send_sms(self, phone_number, message):
        from django.db import connection
        try:
            user_qs = BotUser.objects.filter(phone=phone_number)
            if not user_qs.exists():
                SmsConfirm.objects.filter(phone=phone_number).delete()
                logger.info("BotService: no BotUser for phone=%s, dropped SMS", phone_number)
                return
            if bot is None:
                logger.warning("BotService: bot not configured, cannot send SMS")
                return
            bot.send_message(user_qs.first().user_id, message)
        finally:
            connection.close()
