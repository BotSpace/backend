"""Komissiya hisoblash va OptionsModel orqali foiz o'qish."""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal

logger = logging.getLogger(__name__)

_DEFAULT_COMMISSION_PERCENT = Decimal("5")
_OPTIONS_KEY = "payment_commission_percent"


def get_commission_percent() -> Decimal:
    """OptionsModel yoki sozlamalardan komissiya foizini o'qiydi.

    OptionsModel'da SettingsModel(key="payment_commission_percent") ostida
    OptionsModel(key="value", value=[...]) sxemasi ishlatiladi.
    Topilmasa default 5 qaytaradi.
    """
    try:
        from core.apps.shared.models.settings import SettingsModel

        setting = SettingsModel.objects.filter(key=_OPTIONS_KEY).first()
        if setting:
            option = setting.options.filter(key="value").first()
            if option and option.value:
                return Decimal(str(option.value[0]))
    except Exception as exc:
        logger.warning("get_commission_percent: OptionsModel o'qishda xato: %s", exc)
    return _DEFAULT_COMMISSION_PERCENT


def calculate_commission(amount: Decimal, percent: Decimal | None = None) -> tuple[Decimal, Decimal]:
    """(commission, net_amount) juftligini hisoblaydi.

    Args:
        amount: To'liq to'lov summasi (so'm).
        percent: Foiz; None bo'lsa OptionsModel/default ishlatiladi.

    Returns:
        (commission, net_amount) — ikkalasi ham Decimal, 2 kasr.
    """
    if percent is None:
        percent = get_commission_percent()
    commission = (amount * percent / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    net_amount = (amount - commission).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return commission, net_amount
