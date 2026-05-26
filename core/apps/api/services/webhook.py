import logging
from typing import Literal
from httpx import Client, Timeout
import httpx

from core.apps.api.exceptions.bot import BotTokenNotFound
from config.env import env
from core.apps.api.exceptions.wabhook import WebhookConnectionError, WebhookInvalidStatusCode
from core.apps.api.models.project import ProjectModel
from core.apps.api.services.enviroment import release_bot_token

WEBHOOK_MODE = Literal["release", "debug"]


def service_send_webhook(service_name, payload):
    timeout_config = Timeout(connect=10, read=30, write=30, pool=10)
    client = Client(timeout=timeout_config)
    try:
        response = client.post("http://%s:8000" % service_name, json=payload)
    except httpx.ConnectError:
        raise WebhookConnectionError("Connection error")
    if response.status_code != 200:
        raise WebhookInvalidStatusCode("invalid status code %s" % response.status_code)
    return True


def set_webhook(instance: ProjectModel, mode: WEBHOOK_MODE):
    base_url = "https://%(domain)s/api/bot-webhook/%(mode)s/" % {
        "domain": env.str("DOMAIN", "api.botmother.uz"),
        "mode": mode,
    }
    token = ""
    if mode == "debug":
        return True
    elif mode == "release":
        url = base_url + str(instance.release_webhook_uuid) + "/"
        token = release_bot_token(instance.pk)
    else:
        raise ValueError("Invalid webhook mode")
    if not token:
        raise BotTokenNotFound()
    response = httpx.post("https://api.telegram.org/bot%s/setWebhook?url=%s" % (token, url))
    logging.info("set webhook response=%s", response.content)
    return response.status_code == 200
