"""Concrete implementation of BalanceService.

Module-level functions are kept for backwards compatibility with existing
call sites; new code SHOULD depend on the BalanceService protocol or the
default instance ``balance_service``.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import F

from core.contracts.balance import Amount, BalanceService
from core.apps.payment.models.history import HistoryModel

logger = logging.getLogger(__name__)

User = get_user_model()


class DjangoBalanceService:
    """Default BalanceService implementation backed by Django ORM."""

    @transaction.atomic
    def add(
        self,
        user,
        amount: Amount,
        *,
        comment: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> None:
        delta = int(Decimal(amount))
        if delta < 0:
            raise ValueError("add() amount must be non-negative; use subtract()")
        self._apply(user, delta, kind="income", comment=comment, idempotency_key=idempotency_key)

    @transaction.atomic
    def subtract(
        self,
        user,
        amount: Amount,
        *,
        comment: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> None:
        delta = int(Decimal(amount))
        if delta < 0:
            raise ValueError("subtract() amount must be non-negative")
        self._apply(user, -delta, kind="expense", comment=comment, idempotency_key=idempotency_key)

    def _apply(
        self,
        user,
        signed_delta: int,
        *,
        kind: str,
        comment: Optional[str],
        idempotency_key: Optional[str],
    ) -> None:
        # idempotency_key is honored once HistoryModel carries the field (phase 5).
        # The constraint there ensures the unique-violation path replaces this check.
        history_kwargs = {
            "user": user,
            "amount": Decimal(abs(signed_delta)),
            "type": kind,
            "comment": comment,
        }
        if idempotency_key and "idempotency_key" in {f.name for f in HistoryModel._meta.get_fields()}:
            history_kwargs["idempotency_key"] = idempotency_key

        User.objects.filter(pk=user.pk).update(balance=F("balance") + signed_delta)
        user.refresh_from_db(fields=["balance"])

        try:
            HistoryModel.objects.create(**history_kwargs)
        except IntegrityError:
            User.objects.filter(pk=user.pk).update(balance=F("balance") - signed_delta)
            logger.warning(
                "balance idempotency race: user=%s key=%s — reverted", user.pk, idempotency_key
            )
            return


balance_service: BalanceService = DjangoBalanceService()


def add_balance(user, amount: Amount, comment: Optional[str] = None, *, idempotency_key: Optional[str] = None) -> None:
    """Backwards-compatible wrapper around balance_service.add."""
    balance_service.add(user, amount, comment=comment, idempotency_key=idempotency_key)


def subtract_balance(user, amount: Amount, comment: Optional[str] = None, *, idempotency_key: Optional[str] = None) -> None:
    """Backwards-compatible wrapper around balance_service.subtract."""
    balance_service.subtract(user, amount, comment=comment, idempotency_key=idempotency_key)
