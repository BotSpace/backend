from telebot import TeleBot

from config.env import env

try:
    bot = TeleBot(str(env.str("BOT_TOKEN")))
except Exception as e:
    print(e)
    bot = None
