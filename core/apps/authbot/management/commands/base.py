import logging

from telebot import TeleBot

from config.env import env

logger = logging.getLogger(__name__)

_token = env.str("BOT_TOKEN", default="")
if _token:
    try:
        bot = TeleBot(_token)
    except Exception:
        logger.exception("TeleBot initialization failed")
        bot = None
else:
    logger.info("BOT_TOKEN not set — authbot disabled")
    bot = None
