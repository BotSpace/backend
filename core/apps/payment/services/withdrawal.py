"""Bot daromadidan yechiladigan balansni hisoblash.

Umumiy ``User.balance`` foydalanuvchi o'zi to'ldirgan pullarni ham o'z ichiga
oladi. Pul yechishda esa faqat bot to'lovlaridan tushgan sof daromad
yechilishi kerak. Shu sababli yechiladigan balans alohida hisoblanadi:

    yechiladigan = (paid orderlar net_amount yig'indisi)
                   − (pending + approved yechishlar yig'indisi)
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from core.apps.payment.enums.payment import PaymentOrderStatusEnum
from core.apps.payment.enums.withdrawal import WithdrawalStatusEnum
from core.apps.payment.models.order import PaymentOrderModel
from core.apps.payment.models.withdrawal import WithdrawalRequestModel


def get_bot_earned(user) -> Decimal:
    """Botlardan tushgan jami sof daromad (paid orderlar net_amount)."""
    return PaymentOrderModel.objects.filter(
        owner=user,
        status=PaymentOrderStatusEnum.PAID,
    ).aggregate(total=Coalesce(Sum("net_amount"), Decimal("0")))["total"]


def get_reserved(user) -> Decimal:
    """Kutilayotgan va tasdiqlangan yechishlar yig'indisi (band qilingan)."""
    return WithdrawalRequestModel.objects.filter(
        user=user,
        status__in=[WithdrawalStatusEnum.PENDING.value, WithdrawalStatusEnum.APPROVED.value],
    ).aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]


def get_withdrawable_balance(user) -> Decimal:
    """Hozir yechish mumkin bo'lgan bot daromadi (manfiy bo'lmaydi)."""
    withdrawable = get_bot_earned(user) - get_reserved(user)
    return withdrawable if withdrawable > 0 else Decimal("0")
