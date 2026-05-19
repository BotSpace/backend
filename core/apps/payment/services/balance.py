from decimal import Decimal
from typing import Optional, Union

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F

from core.apps.payment.models.history import HistoryModel


User = get_user_model()

Amount = Union[int, float, str, Decimal]


@transaction.atomic
def add_balance(user, amount: Amount, comment: Optional[str] = None) -> None:
    """User hisobiga pulni atomic tarzda qo'shadi.

    F() expression yordamida race condition'lardan himoyalangan.

    Args:
        user: User instansiyasi (yangilanadi).
        amount: qo'shiladigan summa.
        comment: tarix yozuvi izohi.
    """
    delta = int(Decimal(amount))
    User.objects.filter(pk=user.pk).update(balance=F("balance") + delta)
    user.refresh_from_db(fields=["balance"])
    HistoryModel.objects.create(
        user=user,
        amount=Decimal(amount),
        type="income",
        comment=comment,
    )


@transaction.atomic
def subtract_balance(user, amount: Amount, comment: Optional[str] = None) -> None:
    """User hisobidan pulni atomic tarzda yechadi.

    F() expression yordamida race condition'lardan himoyalangan.

    Args:
        user: User instansiyasi (yangilanadi).
        amount: yechiladigan summa.
        comment: tarix yozuvi izohi.
    """
    delta = int(Decimal(amount))
    User.objects.filter(pk=user.pk).update(balance=F("balance") - delta)
    user.refresh_from_db(fields=["balance"])
    HistoryModel.objects.create(
        user=user,
        amount=Decimal(amount),
        type="expense",
        comment=comment,
    )
