"""Order yaratish API testlari.

Test qamrovi:
- Internal token bilan yaratish — 201
- Tokensiz — 401
- amount < 1000 — 400
- Yo'q loyiha — 404
- Idempotency: bir xil key bilan ikkita POST → bir xil order
- Order yaratilganda TransactionModel ham yaratiladi + pay_url txn.pk bilan
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker
from rest_framework.test import APIClient

from core.apps.api.models.project import ProjectModel
from core.apps.payment.enums.payment import PaymentOrderStatusEnum
from core.apps.payment.models.order import PaymentOrderModel
from core.apps.payment.models.transaction import TransactionModel

User = get_user_model()

ENDPOINT = "/api/payment/order/create/"
INTERNAL_TOKEN = "test-internal-token"


@pytest.fixture
def internal_client(settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    client = APIClient()
    client.credentials(HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN)
    return client


@pytest.fixture
def project(user):
    return baker.make(ProjectModel, owner=user, name="Test Bot")


@pytest.fixture(autouse=True)
def mock_pay_url():
    """Click ClickUp.initializer.generate_pay_link ni mock qiladi."""
    with patch(
        "core.apps.payment.views.order._generate_pay_url",
        return_value="https://click.uz/pay/test",
    ):
        yield


@pytest.mark.django_db
def test_order_create_success(internal_client, project, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    response = internal_client.post(
        ENDPOINT,
        {"project_id": project.pk, "payer_chat_id": 123456789, "amount": "5000.00"},
        format="json",
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["order_id"]
    assert data["pay_url"] == "https://click.uz/pay/test"
    assert Decimal(data["amount"]) == Decimal("5000.00")
    assert Decimal(data["net_amount"]) == Decimal("4750.00")  # 5% komissiya
    assert Decimal(data["commission"]) == Decimal("250.00")

    order = PaymentOrderModel.objects.get(pk=data["order_id"])
    assert order.status == PaymentOrderStatusEnum.CREATED
    assert order.owner == project.owner


@pytest.mark.django_db
def test_order_create_no_token_returns_401(api_client, project):
    response = api_client.post(
        ENDPOINT,
        {"project_id": project.pk, "payer_chat_id": 111, "amount": "5000"},
        format="json",
    )
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_order_create_amount_below_minimum_returns_400(internal_client, project, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    response = internal_client.post(
        ENDPOINT,
        {"project_id": project.pk, "payer_chat_id": 111, "amount": "999"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_order_create_unknown_project_returns_404(internal_client, settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    response = internal_client.post(
        ENDPOINT,
        {"project_id": 999999, "payer_chat_id": 111, "amount": "5000"},
        format="json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_order_create_idempotency_pending_reuse(internal_client, project, settings):
    """CREATED (pending) order — bir xil key bilan qayta so'rov bir xil order'ni qaytaradi."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    body = {
        "project_id": project.pk,
        "payer_chat_id": 123,
        "amount": "2000",
        "idempotency_key": "uniq-key-abc",
    }
    r1 = internal_client.post(ENDPOINT, body, format="json")
    r2 = internal_client.post(ENDPOINT, body, format="json")

    assert r1.status_code == 201
    assert r2.json()["data"]["order_id"] == r1.json()["data"]["order_id"]
    assert PaymentOrderModel.objects.filter(idempotency_key="uniq-key-abc").count() == 1


@pytest.mark.django_db
def test_order_create_idempotency_paid_creates_new_order(internal_client, project, settings):
    """PAID order — bir xil key bilan qayta so'rov YANGI order yaratadi."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    body = {
        "project_id": project.pk,
        "payer_chat_id": 456,
        "amount": "3000",
        "idempotency_key": "paid-key-xyz",
    }
    r1 = internal_client.post(ENDPOINT, body, format="json")
    assert r1.status_code == 201
    order_id_1 = r1.json()["data"]["order_id"]

    # Order'ni PAID holatiga o'tkazamiz
    PaymentOrderModel.objects.filter(pk=order_id_1).update(status=PaymentOrderStatusEnum.PAID)

    r2 = internal_client.post(ENDPOINT, body, format="json")
    assert r2.status_code == 201
    order_id_2 = r2.json()["data"]["order_id"]

    assert order_id_2 != order_id_1, "Paid order reuse qilinmasligi kerak — yangi order yaratilishi shart"
    # Yangi order key bilan saqlanadi, eski paid order'ning key'i NULL bo'ladi
    assert PaymentOrderModel.objects.filter(idempotency_key="paid-key-xyz").count() == 1
    new_order = PaymentOrderModel.objects.get(pk=order_id_2)
    assert new_order.idempotency_key == "paid-key-xyz"
    old_order = PaymentOrderModel.objects.get(pk=order_id_1)
    assert old_order.idempotency_key is None


@pytest.mark.django_db
def test_order_create_idempotency_cancelled_creates_new_order(internal_client, project, settings):
    """CANCELLED order — bir xil key bilan qayta so'rov YANGI order yaratadi."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN
    body = {
        "project_id": project.pk,
        "payer_chat_id": 789,
        "amount": "4000",
        "idempotency_key": "cancelled-key-xyz",
    }
    r1 = internal_client.post(ENDPOINT, body, format="json")
    assert r1.status_code == 201
    order_id_1 = r1.json()["data"]["order_id"]

    PaymentOrderModel.objects.filter(pk=order_id_1).update(status=PaymentOrderStatusEnum.CANCELLED)

    r2 = internal_client.post(ENDPOINT, body, format="json")
    assert r2.status_code == 201
    order_id_2 = r2.json()["data"]["order_id"]

    assert order_id_2 != order_id_1, "Cancelled order reuse qilinmasligi kerak"
    new_order = PaymentOrderModel.objects.get(pk=order_id_2)
    assert new_order.idempotency_key == "cancelled-key-xyz"
    old_order = PaymentOrderModel.objects.get(pk=order_id_1)
    assert old_order.idempotency_key is None


@pytest.mark.django_db
def test_order_create_creates_transaction_and_pay_url_uses_txn_pk(internal_client, project, settings):
    """Order yaratilganda TransactionModel ham yaratilishi va pay_url txn.pk bilan."""
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN

    captured = {}

    def fake_generate(txn_pk, amount, provider):
        captured["txn_pk"] = txn_pk
        return f"https://click.uz/pay/{txn_pk}"

    with patch("core.apps.payment.views.order._generate_pay_url", side_effect=fake_generate):
        response = internal_client.post(
            ENDPOINT,
            {"project_id": project.pk, "payer_chat_id": 111, "amount": "3000"},
            format="json",
        )

    assert response.status_code == 201
    data = response.json()["data"]

    order = PaymentOrderModel.objects.get(pk=data["order_id"])
    assert order.transaction_id is not None

    txn = TransactionModel.objects.get(pk=order.transaction_id)
    assert txn.amount == Decimal("3000")
    assert txn.user == project.owner

    # pay_url txn.pk bilan yaratilgan
    assert captured["txn_pk"] == txn.pk
    assert data["pay_url"] == f"https://click.uz/pay/{txn.pk}"
