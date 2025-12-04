# type: ignore
"""
Celery tasks for chat functionality with Telegram Bot API rate limiting
"""
from celery import shared_task
from django.core.cache import cache
import requests
import time
import logging

logger = logging.getLogger(__name__)

# Rate limiting constants (Telegram Bot API limits)
RATE_LIMIT_PER_BOT = 30  # messages per second per bot
RATE_LIMIT_PER_CHAT = 1  # message per second per chat


@shared_task(bind=True, max_retries=3)
def send_telegram_message(self, bot_token, chat_id, text=None, file_path=None, file_type=None):
    """
    Send message to user via Telegram Bot API with rate limiting
    
    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
        text: Message text or caption (optional)
        file_path: Path to file to send (optional)
        file_type: Type of file (photo, video, audio, document) - required if file_path provided
    
    Rate Limiting:
        - 30 messages per second per bot (global)
        - 1 message per second per chat
    """
    try:
        # Check rate limits
        if not check_rate_limit(bot_token, chat_id):
            # Retry after 1 second if rate limited
            raise self.retry(countdown=1)
        
        # Prepare Telegram API URL
        base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Send message based on type
        if file_path and file_type:
            # Send media message
            result = send_media_message(base_url, chat_id, text, file_path, file_type)
        else:
            # Send text message
            result = send_text_message(base_url, chat_id, text)
        
        if not result:
            raise Exception("Failed to send message via Telegram")
        
        logger.info(f"Message sent to chat {chat_id} successfully")
        return {"success": True, "telegram_message_id": result.get("message_id")}
        
    except Exception as e:
        logger.error(f"Error sending Telegram message to {chat_id}: {str(e)}")
        
        # Retry on error (max 3 times)
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


def check_rate_limit(bot_token, chat_id):
    """
    Check if we can send message respecting Telegram rate limits
    
    Returns:
        bool: True if we can send, False if rate limited
    """
    current_time = time.time()
    
    # Check per-bot rate limit (30 msg/sec)
    bot_key = f"telegram_rate_limit_bot:{bot_token[:10]}"
    bot_messages = cache.get(bot_key, [])
    # Remove messages older than 1 second
    bot_messages = [ts for ts in bot_messages if current_time - ts < 1]
    
    if len(bot_messages) >= RATE_LIMIT_PER_BOT:
        logger.warning(f"Bot rate limit reached: {len(bot_messages)} messages in last second")
        return False
    
    # Check per-chat rate limit (1 msg/sec)
    chat_key = f"telegram_rate_limit_chat:{chat_id}"
    last_message_time = cache.get(chat_key, 0)
    
    if current_time - last_message_time < 1:
        logger.warning(f"Chat {chat_id} rate limit reached: last message was {current_time - last_message_time}s ago")
        return False
    
    # Update rate limit counters
    bot_messages.append(current_time)
    cache.set(bot_key, bot_messages, timeout=2)  # Keep for 2 seconds
    cache.set(chat_key, current_time, timeout=2)  # Keep for 2 seconds
    
    return True


def send_text_message(base_url, chat_id, text):
    """Send text message via Telegram Bot API"""
    url = f"{base_url}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text or "No message",
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("ok"):
            return result.get("result")
        else:
            logger.error(f"Telegram API error: {result.get('description')}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return None


def send_media_message(base_url, chat_id, caption, file_path, file_type):
    """Send media message via Telegram Bot API"""
    from django.core.files.storage import default_storage
    
    # Map file types to Telegram API methods
    method_map = {
        "photo": "sendPhoto",
        "video": "sendVideo",
        "audio": "sendAudio",
        "document": "sendDocument"
    }
    
    method = method_map.get(file_type, "sendDocument")
    url = f"{base_url}/{method}"
    
    # Open file from storage
    try:
        with default_storage.open(file_path, 'rb') as file:
            files = {
                file_type: file.read()
            }
            
            data = {
                "chat_id": chat_id,
            }
            
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "HTML"
            
            response = requests.post(url, data=data, files=files, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                return result.get("result")
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return None
                
    except Exception as e:
        logger.error(f"Error sending media: {str(e)}")
        return None
