import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def fetch_managed_bot_token(bot_user_id: int) -> str | None:
    """getManagedBotToken Telegram API chaqiruvi."""
    manager_token = getattr(settings, "MANAGER_BOT_TOKEN", "")
    if not manager_token:
        logger.error("MANAGER_BOT_TOKEN sozlanmagan")
        return None
    try:
        resp = httpx.get(
            f"https://api.telegram.org/bot{manager_token}/getManagedBotToken",
            params={"user_id": bot_user_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result")
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return result.get("token")
        logger.error("getManagedBotToken: kutilmagan result formati: %s", result)
        return None
    except Exception as exc:
        logger.error("getManagedBotToken xatosi: %s", exc)
        return None


def set_manager_webhook() -> bool:
    """Manager bot uchun Telegram webhook o'rnatish."""
    manager_token = getattr(settings, "MANAGER_BOT_TOKEN", "")
    secret = getattr(settings, "MANAGER_BOT_WEBHOOK_SECRET", "")
    domain = getattr(settings, "DOMAIN", "api.botspace.uz")
    if not manager_token or not secret:
        logger.error("MANAGER_BOT_TOKEN yoki MANAGER_BOT_WEBHOOK_SECRET yo'q")
        return False
    url = f"https://{domain}/api/managed-bot/webhook/{secret}/"
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{manager_token}/setWebhook",
            json={
                "url": url,
                "allowed_updates": ["managed_bot"],
                "secret_token": secret,
            },
            timeout=10,
        )
        ok = resp.json().get("ok", False)
        logger.info("setWebhook manager bot: ok=%s url=%s", ok, url)
        return ok
    except Exception as exc:
        logger.error("setWebhook manager bot xatosi: %s", exc)
        return False
