from core.apps.shared.models import OptionsModel
from typing import Optional
from django.utils.translation import gettext_lazy as _
from django.conf import settings


def get_config(settings: str, key: str, default=None) -> Optional[str]:
    config = OptionsModel.objects.filter(settings__key=settings, key=key)
    if not config.exists():
        return default
    return config.first().value


def engine_version() -> str:
    engine_version = get_config("engine", "version")
    if engine_version is None:
        return settings.ENGINE_VERSION
    return engine_version[0]


def get_exchange_rate():
    exchange_rate = get_config("currency", "exchange_rate")
    if exchange_rate is None:
        raise Exception(_("USD kursi kiritilmagan iltimos adminga murojat qiling"))
    return float(exchange_rate[0])


def _config_first(settings_key: str, key: str, fallback: str = "") -> str:
    """Dynamic config (admin panel)dan birinchi qiymat; bo'lmasa fallback."""
    value = get_config(settings_key, key)
    if value:
        return value[0]
    return fallback


def paycue_api_token() -> str:
    """Paycue api token (transaction yaratish) — admin panel config, env fallback."""
    return _config_first("paycue", "api_token", getattr(settings, "PAYCUE_API_KEY", ""))


def paycue_webhook_token() -> str:
    """Paycue webhook token (webhook tekshirish) — admin panel config, env fallback."""
    fallback = getattr(settings, "PAYCUE_WEBHOOK_KEY", "") or getattr(settings, "PAYCUE_API_KEY", "")
    return _config_first("paycue", "webhook_token", fallback)


def paycue_card_id() -> int:
    """Paycue card id — admin panel config, env fallback (token bilan bog'liq)."""
    raw = _config_first("paycue", "card_id", str(getattr(settings, "PAYCUE_CARD_ID", 0)))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0
