import logging
from telebot import types
from ..management.commands.base import bot
from django.utils.translation import gettext as _
from .. import keyboards, messages
from ..models import BotUser, Code


def start_handler(message: types.Message):
    bot.send_message(
        message.chat.id,
        _("Assalomu Aleykum botga xush kelibsiz! 👋"),
        reply_markup=keyboards.send_phone,
    )


def phone_handler(message: types.Message):
    from django.db import connection
    try:
        phone = str(message.contact.phone_number).replace("+", "")
        user, _ = BotUser.objects.get_or_create(
            user_id=message.from_user.id,
            phone=phone,
            defaults={
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
            },
        )
        code = Code.objects.get_or_create_code(user.id)
        sent_message = bot.send_message(
            message.chat.id,
            messages.you_otp.format(code.code),
            parse_mode="markdown",
        )
        code.message_id = sent_message.id
        code.save()
        connection.close()
    except Exception as e:
        logging.critical("send confirm code error error=%s", e)
        bot.send_message(message.chat.id, str(e))
        connection.close()
