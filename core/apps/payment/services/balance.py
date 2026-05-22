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
        history_kwargs = {
            "user": user,
            "amount": Decimal(abs(signed_delta)),
            "type": kind,
            "comment": comment,
        }
        if idempotency_key and "idempotency_key" in {f.name for f in HistoryModel._meta.get_fields()}:
            history_kwargs["idempotency_key"] = idempotency_key

        # Insert history FIRST inside a savepoint so an idempotency_key
        # collision rolls back the inner block (without poisoning the outer
        # @transaction.atomic) and we treat the call as a no-op.
        try:
            with transaction.atomic():
                HistoryModel.objects.create(**history_kwargs)
                User.objects.filter(pk=user.pk).update(balance=F("balance") + signed_delta)
        except IntegrityError:
            logger.warning(
                "balance idempotency: user=%s key=%s already applied — skipping",
                user.pk,
                idempotency_key,
            )
            user.refresh_from_db(fields=["balance"])
            return

        user.refresh_from_db(fields=["balance"])


balance_service: BalanceService = DjangoBalanceService()


def add_balance(user, amount: Amount, comment: Optional[str] = None, *, idempotency_key: Optional[str] = None) -> None:
    """Backwards-compatible wrapper around balance_service.add."""
    balance_service.add(user, amount, comment=comment, idempotency_key=idempotency_key)


def subtract_balance(user, amount: Amount, comment: Optional[str] = None, *, idempotency_key: Optional[str] = None) -> None:
    """Backwards-compatible wrapper around balance_service.subtract."""
    balance_service.subtract(user, amount, comment=comment, idempotency_key=idempotency_key)
