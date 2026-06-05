"""Earnings API testlari.

Test qamrovi:
- Egasi faqat o'z paid orderlarini ko'radi
- Boshqa eganing orderlarini ko'ra olmaydi
- Balans + summa to'g'ri hisoblanadi
- Filter (project_id, status) ishlaydi
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from model_bakery import baker
from rest_framework.test import APIClient

from core.apps.api.models.project import ProjectModel
from core.apps.payment.enums.payment import PaymentOrderStatusEnum
from core.apps.payment.models.order import PaymentOrderModel

User = get_user_model()

ENDPOINT = "/api/earnings/"


@pytest.fixture
def owner(db):
    u = User._create_fake()
    u.balance = 9500
    u.save(update_fields=["balance"])
    return u


@pytest.fixture
def other_owner(db):
    return baker.make(User, phone="+998901234567")


@pytest.fixture
def project(owner):
    return baker.make(ProjectModel, owner=owner, name="My Bot")


@pytest.fixture
def other_project(other_owner):
    return baker.make(ProjectModel, owner=other_owner, name="Other Bot")


@pytest.fixture
def paid_order(owner, project):
    return PaymentOrderModel.objects.create(
        project=project,
        owner=owner,
        payer_chat_id=111,
        amount=Decimal("10000"),
        commission=Decimal("500"),
        net_amount=Decimal("9500"),
        status=PaymentOrderStatusEnum.PAID,
    )


@pytest.fixture
def other_owner_order(other_owner, other_project):
    return PaymentOrderModel.objects.create(
        project=other_project,
        owner=other_owner,
        payer_chat_id=222,
        amount=Decimal("5000"),
        commission=Decimal("250"),
        net_amount=Decimal("4750"),
        status=PaymentOrderStatusEnum.PAID,
    )


@pytest.fixture
def auth_client_owner(owner):
    c = APIClient()
    c.force_authenticate(user=owner)
    return c


@pytest.mark.django_db
def test_earnings_returns_own_orders(auth_client_owner, paid_order, other_owner_order):
    response = auth_client_owner.get(ENDPOINT)
    assert response.status_code == 200

    data = response.json().get("data") or response.json()
    orders = data.get("orders") or []
    order_ids = [o["id"] for o in orders]

    assert paid_order.pk in order_ids
    assert other_owner_order.pk not in order_ids


@pytest.mark.django_db
def test_earnings_unauthenticated_returns_401(api_client, paid_order):
    response = api_client.get(ENDPOINT)
    assert response.status_code == 401


@pytest.mark.django_db
def test_earnings_balance_included(auth_client_owner, paid_order):
    response = auth_client_owner.get(ENDPOINT)
    assert response.status_code == 200

    data = response.json().get("data") or response.json()
    assert "balance" in data
    assert data["balance"] == 9500


@pytest.mark.django_db
def test_earnings_only_paid_orders(owner, project, auth_client_owner):
    """Created/cancelled orderlar ko'rinmaydi."""
    PaymentOrderModel.objects.create(
        project=project,
        owner=owner,
        payer_chat_id=333,
        amount=Decimal("3000"),
        status=PaymentOrderStatusEnum.CREATED,
    )
    response = auth_client_owner.get(ENDPOINT)
    data = response.json().get("data") or response.json()
    orders = data.get("orders") or []
    for o in orders:
        assert o["status"] == PaymentOrderStatusEnum.PAID


@pytest.mark.django_db
def test_earnings_filter_by_project(owner, project, auth_client_owner, paid_order):
    other_project2 = baker.make(ProjectModel, owner=owner)
    PaymentOrderModel.objects.create(
        project=other_project2,
        owner=owner,
        payer_chat_id=444,
        amount=Decimal("8000"),
        commission=Decimal("400"),
        net_amount=Decimal("7600"),
        status=PaymentOrderStatusEnum.PAID,
    )

    response = auth_client_owner.get(ENDPOINT, {"project_id": project.pk})
    data = response.json().get("data") or response.json()
    orders = data.get("orders") or []
    assert all(o["project_id"] == project.pk for o in orders)
    assert len(orders) == 1
