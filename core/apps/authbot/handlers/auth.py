# type: ignore
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
                "username": message.from_user.username,
            },
        )
        code = Code.objects.get_or_create_code(user.id)
        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(
            text="Kirish 🔐", url=f"https://botspace.uz/uz/auth?callbackUrl=%2F&code={code.code}"
        )
        markup.add(button)

        sent_message = bot.send_message(
            message.chat.id,
            messages.you_otp.format(code.code),
            parse_mode="Markdown",
            reply_markup=markup,
        )
        code.message_id = sent_message.id
        code.save()
        connection.close()
    except Exception as e:
        logging.critical("send confirm code error error=%s", e)
        bot.send_message(message.chat.id, str(e))
        connection.close()
