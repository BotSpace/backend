"""Click webhook PaymentOrder oqimi testlari.

Test qamrovi:
- Webhook success → egasi balansi net qadar oshadi
- Komissiya BOTSPACE_REVENUE_USER_ID bilan yoziladi
- Ikki marta webhook → bir marta kredit (idempotency)
- Cancelled → refund (subtract) idempotent
- Eski raqamli merchant_trans_id (txn.pk, payment_order yo'q) → subscription oqimi buzilmagan
- Yangi oqim: TransactionModel.pk → PaymentOrder topiladi → order oqimi
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker

from core.apps.api.models.project import ProjectModel
from core.apps.payment.enums.payment import PaymentOrderStatusEnum
from core.apps.payment.models.history import HistoryModel
from core.apps.payment.models.order import PaymentOrderModel
from core.apps.payment.models.transaction import TransactionModel
from core.apps.payment.views.click import ClickWebhookAPIView

User = get_user_model()


@pytest.fixture
def owner(db):
    return User._create_fake()


@pytest.fixture
def project(owner):
    return baker.make(ProjectModel, owner=owner, name="Test Bot")


@pytest.fixture
def txn(owner):
    return TransactionModel.objects.create(user=owner, amount=Decimal("10000"))


@pytest.fixture
def order(project, owner, txn):
    return PaymentOrderModel.objects.create(
        project=project,
        owner=owner,
        payer_chat_id=123456,
        amount=Decimal("10000"),
        commission=Decimal("500"),
        net_amount=Decimal("9500"),
        status=PaymentOrderStatusEnum.CREATED,
        transaction=txn,
    )


@pytest.fixture(autouse=True)
def disable_notify():
    """Engine notify'ni mock qilamiz — test muhitida engine yo'q."""
    with patch("core.apps.payment.views.click.notify_bot_payment", return_value=True):
        yield


# ---------- success oqimi ----------

@pytest.mark.django_db
def test_webhook_order_success_credits_net(order, txn, owner):
    view = ClickWebhookAPIView()
    params = SimpleNamespace(merchant_trans_id=txn.pk, click_trans_id="click-111")

    view.successfully_payment(params)

    owner.refresh_from_db()
    # net_amount = 10000 - 5% = 9500
    assert owner.balance == 9500
    assert HistoryModel.objects.filter(user=owner, type="income").count() == 1

    order.refresh_from_db()
    assert order.status == PaymentOrderStatusEnum.PAID
    assert order.paid_at is not None
    assert order.commission == Decimal("500")
    assert order.net_amount == Decimal("9500")


@pytest.mark.django_db
def test_webhook_order_success_idempotent(order, txn, owner):
    """Ikki marta webhook kelsa faqat bir marta kredit."""
    view = ClickWebhookAPIView()
    params = SimpleNamespace(merchant_trans_id=txn.pk, click_trans_id="click-222")

    view.successfully_payment(params)
    view.successfully_payment(params)  # retry

    owner.refresh_from_db()
    assert owner.balance == 9500
    assert HistoryModel.objects.filter(user=owner, type="income").count() == 1


@pytest.mark.django_db
def test_webhook_order_success_botspace_commission(order, txn, owner, settings):
    """BOTSPACE_REVENUE_USER_ID o'rnatilgan bo'lsa komissiya kreditlanadi."""
    revenue_user = baker.make(User)
    settings.BOTSPACE_REVENUE_USER_ID = revenue_user.pk

    view = ClickWebhookAPIView()
    params = SimpleNamespace(merchant_trans_id=txn.pk, click_trans_id="click-333")
    view.successfully_payment(params)

    revenue_user.refresh_from_db()
    assert revenue_user.balance == 500  # komissiya


# ---------- cancelled oqimi ----------

@pytest.mark.django_db
def test_webhook_order_cancelled_refunds_if_paid(order, txn, owner):
    """Agar to'langan bo'lsa cancelled → subtract."""
    view = ClickWebhookAPIView()
    success_params = SimpleNamespace(merchant_trans_id=txn.pk, click_trans_id="click-444")
    cancel_params = SimpleNamespace(merchant_trans_id=txn.pk, click_trans_id="click-444")

    view.successfully_payment(success_params)
    view.cancelled_payment(cancel_params)

    owner.refresh_from_db()
    assert owner.balance == 0
    assert HistoryModel.objects.filter(user=owner, type="expense").count() == 1


@pytest.mark.django_db
def test_webhook_order_cancelled_idempotent(order, txn, owner):
    """Cancelled webhook ikki marta kelsa bir marta subtract."""
    view = ClickWebhookAPIView()
    success_params = SimpleNamespace(merchant_trans_id=txn.pk, click_trans_id="click-555")
    cancel_params = SimpleNamespace(merchant_trans_id=txn.pk)

    view.successfully_payment(success_params)
    view.cancelled_payment(cancel_params)
    view.cancelled_payment(cancel_params)  # retry

    owner.refresh_from_db()
    assert owner.balance == 0
    assert HistoryModel.objects.filter(user=owner, type="expense").count() == 1


@pytest.mark.django_db
def test_webhook_order_cancelled_without_payment(order, txn, owner):
    """To'lov bo'lmasa cancel → balans o'zgarmaydi."""
    view = ClickWebhookAPIView()
    params = SimpleNamespace(merchant_trans_id=txn.pk)

    view.cancelled_payment(params)

    owner.refresh_from_db()
    assert owner.balance == 0
    order.refresh_from_db()
    assert order.status == PaymentOrderStatusEnum.CANCELLED


# ---------- Marshrutlash: subscription oqimi (payment_order yo'q txn) ----------

@pytest.mark.django_db
def test_txn_without_order_routes_to_subscription(owner, db):
    """PaymentOrder bog'liq bo'lmagan TransactionModel → subscription (balance) oqimi."""
    txn = TransactionModel.objects.create(user=owner, amount=Decimal("12000"), status=False)

    view = ClickWebhookAPIView()
    params = SimpleNamespace(merchant_trans_id=txn.pk)

    view.successfully_payment(params)

    owner.refresh_from_db()
    assert owner.balance == 12000
    txn.refresh_from_db()
    assert txn.status is True


@pytest.mark.django_db
def test_order_txn_does_not_touch_subscription_balance(order, txn, owner):
    """PaymentOrder bog'liq txn → order oqimi, txn.user balansi net bilan oshadi (egasi)."""
    view = ClickWebhookAPIView()
    params = SimpleNamespace(merchant_trans_id=txn.pk, click_trans_id="x")

    view.successfully_payment(params)

    # Egasi balansi net bilan oshdi
    owner.refresh_from_db()
    assert owner.balance == 9500

    # txn.status o'zgarmaydi — order oqimida txn.status yangilanmaydi
    txn.refresh_from_db()
    assert txn.status is False
