from telebot import TeleBot

from config.env import env

try:
    bot = TeleBot(str(env.str("BOT_TOKEN")))
    
    # Register handlers for webhook mode
    from ... import handlers
    bot.register_message_handler(commands=["start"], callback=handlers.start_handler)
    bot.register_message_handler(content_types=["contact"], callback=handlers.phone_handler)
    
except Exception as e:
    print(e)
    bot = None
