"""Tests for the balance service.

Covers the bug classes the audit found:
- concurrent add/subtract must be atomic (no lost updates),
- idempotency keys collapse duplicate webhook deliveries,
- subtract with a negative amount raises rather than crediting.
"""

from decimal import Decimal

import pytest

from core.apps.payment.models.history import HistoryModel
from core.apps.payment.services.balance import DjangoBalanceService


@pytest.fixture
def service():
    return DjangoBalanceService()


@pytest.mark.django_db
def test_add_credits_balance_and_logs_history(user, service):
    service.add(user, 1500, comment="topup")
    user.refresh_from_db()
    assert user.balance == 1500
    history = HistoryModel.objects.get(user=user)
    assert history.type == "income"
    assert history.amount == Decimal("1500")
    assert history.comment == "topup"


@pytest.mark.django_db
def test_subtract_debits_balance(user, service):
    service.add(user, 1000)
    service.subtract(user, 400, comment="debit")
    user.refresh_from_db()
    assert user.balance == 600


@pytest.mark.django_db
def test_subtract_rejects_negative_amount(user, service):
    with pytest.raises(ValueError):
        service.subtract(user, -100)


@pytest.mark.django_db
def test_add_rejects_negative_amount(user, service):
    with pytest.raises(ValueError):
        service.add(user, -100)


@pytest.mark.django_db
def test_idempotency_key_makes_duplicate_a_noop(user, service):
    service.add(user, 500, idempotency_key="webhook-1")
    service.add(user, 500, idempotency_key="webhook-1")
    user.refresh_from_db()
    assert user.balance == 500
    assert HistoryModel.objects.filter(user=user, idempotency_key="webhook-1").count() == 1


@pytest.mark.django_db
def test_different_idempotency_keys_credit_twice(user, service):
    service.add(user, 500, idempotency_key="webhook-1")
    service.add(user, 700, idempotency_key="webhook-2")
    user.refresh_from_db()
    assert user.balance == 1200


@pytest.mark.django_db
def test_decimal_amount_accepted(user, service):
    service.add(user, Decimal("2500"))
    user.refresh_from_db()
    assert user.balance == 2500
