"""Balance service contract."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Protocol, Union, runtime_checkable

Amount = Union[int, float, str, Decimal]


@runtime_checkable
class BalanceService(Protocol):
    """Atomic balance mutation operations.

    Implementations MUST be safe under concurrent requests
    (use F() expressions or row-level locks).
    """

    def add(self, user, amount: Amount, *, comment: Optional[str] = None, idempotency_key: Optional[str] = None) -> None:
        ...

    def subtract(self, user, amount: Amount, *, comment: Optional[str] = None, idempotency_key: Optional[str] = None) -> None:
        ...
