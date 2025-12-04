# type: ignore
"""
Celery tasks for chat functionality with Telegram Bot API rate limiting
"""
from celery import shared_task
import requests
from django.core.files.storage import default_storage
import logging

from core.apps.api.models.file import FileModel
from core.apps.api.services.enviroment import release_bot_token

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_telegram_message(self, chat_id, message_type: str, project_id: int, text=None, file_id=None):
    """
    Send message to user via Telegram Bot API with rate limiting

    Args:
        chat_id: Telegram chat ID
        message_type: Message type text,audio,video,photo,file
        project_id: ProjectModel pk
        text: Message text or caption (optional)
        file: FileModel pk
    """
    try:
        bot_token = release_bot_token(project_id)
        base_url = f"https://api.telegram.org/bot{bot_token}"

        if message_type in ["photo", "video", "audio", "file"]:
            result = send_media_message(base_url, chat_id, text, message_type, file_id)
        else:
            result = send_text_message(base_url, chat_id, text)

        if not result:
            raise Exception("Failed to send message via Telegram")

        logger.info(f"Message sent to chat {chat_id} successfully")
        return {"success": True, "telegram_message_id": result.get("message_id")}

    except Exception as e:
        logger.error(f"Error sending Telegram message to {chat_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2**self.request.retries)


def send_text_message(base_url, chat_id, text):
    """Send text message via Telegram Bot API"""
    url = f"{base_url}/sendMessage"

    payload = {"chat_id": chat_id, "text": text or "No message", "parse_mode": "HTML"}

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


def send_media_message(base_url, chat_id, caption, message_type, file_id: int):
    """Send media message via Telegram Bot API"""

    method_map = {
        "photo": "sendPhoto",
        "video": "sendVideo",
        "audio": "sendAudio",
        "document": "sendDocument",
        "file": "sendDocument",
    }

    method = method_map.get(message_type, "sendDocument")
    url = f"{base_url}/{method}"
    try:
        try:
            file_instance = FileModel.objects.get(pk=file_id)
        except FileModel.DoesNotExist:
            logging.error("File not found file_id=%s", file_id)
            return
        with file_instance.file.open("rb") as file:
            files = {message_type: file.read()}
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
