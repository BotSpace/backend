from core.apps.authbot.management.commands.base import bot
from core.apps.authbot import handlers

bot.register_message_handler(commands=["start"], callback=handlers.start_handler)
bot.register_message_handler(content_types=["contact"], callback=handlers.phone_handler)
