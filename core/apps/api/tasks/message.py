import logging

from celery import shared_task
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from core.apps.api.models.message import MessageModel
from core.apps.api.services.enviroment import release_bot_token
from core.apps.cms.models import CollectionModel
from core.apps.cms.services import find, get_collection_name
from core.apps.api.enums import MessageStatusEnum


@shared_task
def send_message(message_id: int):
    try:
        message = MessageModel.objects.get(id=message_id)
    except MessageModel.DoesNotExist:
        logging.error(f"Message {message_id} does not exist")
        return

    try:
        collection = CollectionModel.objects.get(project=message.project, name="users")
    except CollectionModel.DoesNotExist:
        logging.error(f"Collection 'users' does not exist for project {message.project.pk}")
        message.status = MessageStatusEnum.FAILED
        message.save()
        return

    # Get bot token from project environment
    token = release_bot_token(message.project.pk)
    if token is None:
        logging.error(f"Bot token not found for project {message.project.pk}")
        message.status = MessageStatusEnum.FAILED
        message.save()
        return

    # Initialize bot
    try:
        bot = telebot.TeleBot(token)
    except Exception as e:
        logging.error(f"Failed to initialize bot: {e}")
        message.status = MessageStatusEnum.FAILED
        message.save()
        return

    # Get users from collection
    users: list = find(get_collection_name(collection))
    
    # Update total count
    message.total = len(users)
    message.save()

    done: int = 0
    fail: int = 0

    # Build keyboard if buttons exist
    keyboard = None
    if message.buttons and len(message.buttons) > 0:
        if message.button_type == "inline":
            keyboard = InlineKeyboardMarkup()
            for row in message.buttons:
                buttons_row = []
                for btn in row:
                    if 'link' in btn and btn['link']:
                        # URL button
                        buttons_row.append(InlineKeyboardButton(
                            text=btn['title'],
                            url=btn['link']
                        ))
                    elif 'callback_data' in btn and btn['callback_data']:
                        # Callback button
                        buttons_row.append(InlineKeyboardButton(
                            text=btn['title'],
                            callback_data=btn['callback_data']
                        ))
                if buttons_row:
                    keyboard.add(*buttons_row)
        elif message.button_type == "reply":
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            for row in message.buttons:
                buttons_row = []
                for btn in row:
                    button = KeyboardButton(text=btn['title'])
                    if btn.get('request_contact'):
                        button.request_contact = True
                    if btn.get('request_location'):
                        button.request_location = True
                    buttons_row.append(button)
                if buttons_row:
                    keyboard.add(*buttons_row)

    # Send message to each user
    for user in users:
        chat_id = user.get("chat_id")
        if chat_id is None:
            fail += 1
            continue

        try:
            if message.message_type == "photo":
                # Send photo with caption
                if message.file:
                    with open(message.file.path, 'rb') as photo:
                        bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=message.caption if message.caption else None,
                            reply_markup=keyboard
                        )
                else:
                    fail += 1
                    continue
            elif message.message_type == "video":
                # Send video with caption
                if message.file:
                    with open(message.file.path, 'rb') as video:
                        bot.send_video(
                            chat_id=chat_id,
                            video=video,
                            caption=message.caption if message.caption else None,
                            reply_markup=keyboard
                        )
                else:
                    fail += 1
                    continue
            else:
                # Send text message
                bot.send_message(
                    chat_id=chat_id,
                    text=message.caption,
                    reply_markup=keyboard
                )
            
            done += 1
            logging.info(f"Message sent to {chat_id}")
        except Exception as e:
            fail += 1
            logging.error(f"Failed to send message to {chat_id}: {e}")

    # Update message status
    message.done = done
    message.fail = fail
    
    if done == message.total:
        message.status = MessageStatusEnum.DONE
    elif fail == message.total:
        message.status = MessageStatusEnum.FAILED
    else:
        message.status = MessageStatusEnum.PROGRESS
    
    message.save()
    
    logging.info(f"Message {message.pk} sent: {done} success, {fail} failed out of {message.total}")
