"""End-to-end tests that the webhook handlers are idempotent.

We bypass the click/payme signature verification (already covered by
the upstream packages) and exercise the handler methods directly, then
assert that re-running them with the same transaction id never credits
or debits the user twice.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.apps.payment.models.history import HistoryModel
from core.apps.payment.models.transaction import TransactionModel
from core.apps.payment.views.click import ClickWebhookAPIView
from core.apps.payment.views.payme import PaymeCallBackAPIView


@pytest.fixture
def pending_transaction(user):
    return TransactionModel.objects.create(user=user, amount=Decimal("12000"), status=False)


# ---------- Click ----------

@pytest.mark.django_db
def test_click_successfully_payment_credits_once(user, pending_transaction):
    view = ClickWebhookAPIView()
    params = SimpleNamespace(merchant_trans_id=pending_transaction.pk)

    view.successfully_payment(params)
    view.successfully_payment(params)  # retry

    user.refresh_from_db()
    assert user.balance == 12000
    assert HistoryModel.objects.filter(user=user, type="income").count() == 1
    pending_transaction.refresh_from_db()
    assert pending_transaction.status is True


@pytest.mark.django_db
def test_click_cancelled_payment_debits_once(user, pending_transaction):
    view = ClickWebhookAPIView()
    params = SimpleNamespace(merchant_trans_id=pending_transaction.pk)

    view.successfully_payment(params)
    view.cancelled_payment(params)
    view.cancelled_payment(params)  # retry

    user.refresh_from_db()
    assert user.balance == 0
    assert HistoryModel.objects.filter(user=user, type="expense").count() == 1


@pytest.mark.django_db
def test_click_missing_transaction_raises(user):
    view = ClickWebhookAPIView()
    params = SimpleNamespace(merchant_trans_id=999999)
    with pytest.raises(ValueError):
        view.successfully_payment(params)


# ---------- Payme ----------

@pytest.mark.django_db
def test_payme_successfully_payment_credits_once(user, pending_transaction):
    view = PaymeCallBackAPIView()
    params = SimpleNamespace(merchant_trans_id=pending_transaction.pk)

    view.handle_successfully_payment(params, result=None)
    view.handle_successfully_payment(params, result=None)  # retry

    user.refresh_from_db()
    assert user.balance == 12000
    assert HistoryModel.objects.filter(user=user, type="income").count() == 1


@pytest.mark.django_db
def test_payme_cancelled_payment_debits_once(user, pending_transaction):
    view = PaymeCallBackAPIView()
    params = SimpleNamespace(merchant_trans_id=pending_transaction.pk)

    view.handle_successfully_payment(params, result=None)
    view.handle_cancelled_payment(params, result=None)
    view.handle_cancelled_payment(params, result=None)  # retry

    user.refresh_from_db()
    assert user.balance == 0
    assert HistoryModel.objects.filter(user=user, type="expense").count() == 1


# ---------- cross-provider isolation ----------

@pytest.mark.django_db
def test_click_and_payme_credit_independently(user, pending_transaction):
    """Different providers use different idempotency namespaces."""
    click = ClickWebhookAPIView()
    payme = PaymeCallBackAPIView()
    params = SimpleNamespace(merchant_trans_id=pending_transaction.pk)

    click.successfully_payment(params)
    payme.handle_successfully_payment(params, result=None)

    user.refresh_from_db()
    assert user.balance == 24000
    assert HistoryModel.objects.filter(user=user, type="income").count() == 2
