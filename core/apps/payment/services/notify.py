"""Engine'ni to'lov haqida xabardor qilish servisi.

To'lov tasdiqlangandan keyin backend release bot engine'iga:
    POST http://bot-{release_webhook_uuid}:8000/custom-webhook/click/{payer_chat_id}
so'rov yuboradi. Engine'da ExternalWebhookTriggerNode(provider="click") ishga tushadi.

In-cluster URL sxemasi:
    Kubernetes Service nomi: bot-{project.release_webhook_uuid}
    Port: 8000 (WEBHOOK_PORT engine env)
    Path: /custom-webhook/click/{payer_chat_id}

Bu Faza 1 implementatsiyasi. Faza 2'da engine'da BotspacePaymentNode pauza/resume
mexanizmi qo'shilgandan keyin kontrakt kengaytiriladi.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from core.apps.payment.models.order import PaymentOrderModel

logger = logging.getLogger(__name__)

# Engine'ning default webhook porti (deploy_engine: WEBHOOK_PORT=8000)
_ENGINE_WEBHOOK_PORT = 8000


def _engine_url(project) -> str | None:
    """Release bot engine'ining in-cluster base URL'ini qaytaradi.

    Service nomi deploy_engine -> create_service: `bot-{release_webhook_uuid}`.
    Kubernetes ClusterIP Service orqali `http://bot-<uuid>:8000` ga murojaat qilinadi.

    Agar release_webhook_uuid yo'q yoki RelaseModel topilmasa None qaytaradi.
    """
    uuid = getattr(project, "release_webhook_uuid", None)
    if not uuid:
        return None
    return f"http://bot-{uuid}:{_ENGINE_WEBHOOK_PORT}"


def notify_bot_payment(order: "PaymentOrderModel") -> bool:
    """To'lov tasdiqlangandan keyin release bot engine'iga POST yuboradi.

    Payload (ExternalWebhookTriggerNode kontrakt):
        order_id        — PaymentOrder.pk
        amount          — to'liq summa (so'm)
        net             — egaga kreditlangan summa
        commission      — Botspace ulushi
        status          — "paid"
        comment         — buyurtma izohi

    Qaytaradi:
        True  — engine 2xx javob berdi
        False — ulanish yoki boshqa xato (webhook bloklanmaydi)

    Faza 2 TODO:
        - BotspacePaymentNode pauza/resume mexanizmi qo'shilgach
          `/custom-webhook/click/{chat_id}?order_id={id}` shaklida
          kontrakt kengaytiriladi.
        - release_webhook_uuid o'rniga RelaseModel.service_id bo'yicha
          dinamik URL qo'llab-quvvatlanadi.
    """
    project = order.project
    base_url = _engine_url(project)
    if not base_url:
        logger.warning(
            "notify_bot_payment: release_webhook_uuid topilmadi, xabardor qilinmadi "
            "order_id=%s project_id=%s",
            order.pk,
            project.pk,
        )
        return False

    url = f"{base_url}/custom-webhook/click/{order.payer_chat_id}"
    payload = {
        "order_id": order.pk,
        "amount": str(order.amount),
        "net": str(order.net_amount),
        "commission": str(order.commission),
        "status": "paid",
        "comment": order.comment or "",
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(connect=5, read=10, write=10, pool=5)) as client:
            response = client.post(url, json=payload)
        if response.status_code < 300:
            logger.info(
                "notify_bot_payment: engine xabardor qilindi order_id=%s project_id=%s status=%s",
                order.pk,
                project.pk,
                response.status_code,
            )
            return True
        logger.warning(
            "notify_bot_payment: engine noto'g'ri status kodi order_id=%s status=%s body=%s",
            order.pk,
            response.status_code,
            response.text[:200],
        )
        return False
    except httpx.ConnectError as exc:
        logger.warning(
            "notify_bot_payment: engine'ga ulanib bo'lmadi order_id=%s url=%s error=%s "
            "(TODO Faza2: engine ishlamayotgan bo'lishi mumkin)",
            order.pk,
            url,
            exc,
        )
        return False
    except Exception as exc:
        logger.error(
            "notify_bot_payment: kutilmagan xato order_id=%s error=%s",
            order.pk,
            exc,
            exc_info=True,
        )
        return False
