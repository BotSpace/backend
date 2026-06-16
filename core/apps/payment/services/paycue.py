"""Paycue client — Humo-karta to'lov avtomatizatsiyasi (UzStack/paycue).

Kontrakt (paycue manbasidan):
  POST {base}/create/transaction/   body: {"amount": <int>}
    → {"status": true,  "data": {"amount": <moslashtirilgan>, "transaction_id": "<uuid>"}}
    → {"status": false, "data": {"detail": "..."}}   (farq 100 so'mdan oshsa)

Paycue so'ralgan summaga eng yaqin BAND bo'lmagan summani topadi (max +100 so'm).
Foydalanuvchi ANIQ o'sha summani Humo kartaga o'tkazadi; paycue webhook bilan
({"action":"confirm|cancel","amount":...,"transaction_id":...}) tasdiqlaydi.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PaycueError(Exception):
    """Paycue xizmati bilan ishlashda xato (ulanib bo'lmadi yoki status=false)."""


def create_transaction(amount: int, *, timeout: int = 15) -> dict:
    """Paycue'da tranzaksiya yaratadi va {amount, transaction_id} qaytaradi.

    `amount` — so'ralgan summa (butun so'm). Qaytgan `amount` — foydalanuvchi
    o'tkazishi kerak bo'lgan MOSLASHTIRILGAN summa (so'ralgandan biroz ko'p).

    Paycue REST API: POST {base}/api/transactions, Authorization: Bearer <token>,
    body {card_id, amount} → {status, data:{amount, card_id, transaction_id}}.
    """
    from core.apps.shared.utils.settings import paycue_api_token, paycue_card_id

    base = settings.PAYCUE_BASE_URL.rstrip("/")
    url = f"{base}/api/transactions"

    card_id = paycue_card_id()
    if card_id <= 0:
        raise PaycueError("paycue card_id sozlanmagan")

    headers = {"Content-Type": "application/json"}
    # Account token — Authorization: Bearer (admin panel config, env fallback).
    api_key = paycue_api_token()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.post(
            url, json={"card_id": card_id, "amount": int(amount)}, headers=headers, timeout=timeout
        )
    except requests.RequestException as exc:
        logger.error("paycue create_transaction: ulanib bo'lmadi url=%s err=%s", url, exc)
        raise PaycueError(f"paycue unreachable: {exc}") from exc

    if resp.status_code >= 300:
        logger.error("paycue create_transaction: status=%s body=%s", resp.status_code, resp.text[:300])
        raise PaycueError(f"paycue returned {resp.status_code}")

    payload = resp.json()
    if not payload.get("status"):
        detail = (payload.get("data") or {}).get("detail", "paycue xato")
        raise PaycueError(str(detail))

    data = payload.get("data") or {}
    txn_id = data.get("transaction_id")
    adjusted = data.get("amount")
    if not txn_id or adjusted is None:
        raise PaycueError(f"paycue response missing fields: {payload}")

    return {"transaction_id": str(txn_id), "amount": int(adjusted)}
