"""Domain service contracts.

Inter-app boundaries are described here as Protocols/ABCs so concrete
implementations from app modules (payment, cms, …) can be injected and
swapped for tests without import cycles.

Usage::

    from core.contracts import BalanceService
    def my_view(balance_service: BalanceService): ...
"""

from .balance import BalanceService
from .mongo import MongoCredentials, MongoCredentialsService, MongoRepository
from .notifications import NotificationService

__all__ = [
    "BalanceService",
    "MongoCredentials",
    "MongoCredentialsService",
    "MongoRepository",
    "NotificationService",
]
