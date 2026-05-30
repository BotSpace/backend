import pytest
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.accounts.models import User
from core.apps.administration.models import AdminAuditLogModel
from core.apps.template.models import TemplateModel
from core.apps.template.models.withdrawal import TemplateWithdrawalRequestModel
from core.apps.template.enums.withdrawal import WithdrawalStatusEnum


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        phone="+998900000001", username="admin", password="x", is_staff=True
    )


@pytest.fixture
def normal_user(db):
    return User.objects.create_user(
        phone="+998900000002", username="user", password="x"
    )


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.fixture
def user_client(normal_user):
    c = APIClient()
    c.force_authenticate(user=normal_user)
    return c


# ── permission gate ──────────────────────────────────────────────────────────

def test_non_admin_forbidden(user_client):
    res = user_client.get("/api/admin/users/")
    assert res.status_code == 403


def test_anonymous_forbidden(db):
    res = APIClient().get("/api/admin/users/")
    assert res.status_code in (401, 403)


def test_admin_can_list_users(admin_client, normal_user):
    res = admin_client.get("/api/admin/users/")
    assert res.status_code == 200


# ── users: ban + balance + audit ─────────────────────────────────────────────

def test_ban_user_writes_audit(admin_client, normal_user):
    res = admin_client.patch(
        f"/api/admin/users/{normal_user.id}/ban/",
        {"is_active": False, "note": "spam"},
        format="json",
    )
    assert res.status_code == 200
    normal_user.refresh_from_db()
    assert normal_user.is_active is False
    log = AdminAuditLogModel.objects.filter(action="user.set_active").first()
    assert log is not None
    assert log.target_id == str(normal_user.id)
    assert log.payload_after == {"is_active": False}


def test_set_balance_writes_audit(admin_client, normal_user):
    res = admin_client.patch(
        f"/api/admin/users/{normal_user.id}/balance/",
        {"field": "balance", "value": "5000", "note": "manual top-up"},
        format="json",
    )
    assert res.status_code == 200
    normal_user.refresh_from_db()
    assert normal_user.balance == 5000
    assert AdminAuditLogModel.objects.filter(action="user.balance.set").exists()


# ── templates: verify ────────────────────────────────────────────────────────

def test_verify_template(admin_client, admin_user):
    tpl = TemplateModel.objects.create(
        name="Test tpl",
        short_description="s",
        description="d",
        original_price=Decimal("0.00"),
        is_verify=False,
        author=admin_user,
    )
    res = admin_client.patch(
        f"/api/admin/templates/{tpl.id}/verify/",
        {"is_verify": True},
        format="json",
    )
    assert res.status_code == 200
    tpl.refresh_from_db()
    assert tpl.is_verify is True
    assert AdminAuditLogModel.objects.filter(action="template.verify").exists()


# ── withdrawals: approve atomicity + double-approve guard ─────────────────────

def _make_withdrawal(user, amount="100.00"):
    user.template_balance = Decimal("500.00")
    user.save()
    return TemplateWithdrawalRequestModel.objects.create(
        user=user,
        amount=Decimal(amount),
        card_number="8600000000000000",
        card_owner="Test Owner",
        status=WithdrawalStatusEnum.PENDING.value,
    )


def test_approve_withdrawal_deducts_balance(admin_client, normal_user):
    w = _make_withdrawal(normal_user, "100.00")
    res = admin_client.patch(
        f"/api/admin/withdrawals/{w.id}/approve/", {}, format="json"
    )
    assert res.status_code == 200
    normal_user.refresh_from_db()
    assert normal_user.template_balance == Decimal("400.00")
    w.refresh_from_db()
    assert w.status == WithdrawalStatusEnum.APPROVED.value
    assert AdminAuditLogModel.objects.filter(action="withdrawal.approve").exists()


def test_double_approve_is_rejected(admin_client, normal_user):
    w = _make_withdrawal(normal_user, "100.00")
    first = admin_client.patch(f"/api/admin/withdrawals/{w.id}/approve/", {}, format="json")
    assert first.status_code == 200
    second = admin_client.patch(f"/api/admin/withdrawals/{w.id}/approve/", {}, format="json")
    assert second.status_code == 409
    normal_user.refresh_from_db()
    # Balance deducted only once
    assert normal_user.template_balance == Decimal("400.00")


def test_reject_withdrawal(admin_client, normal_user):
    w = _make_withdrawal(normal_user, "100.00")
    res = admin_client.patch(
        f"/api/admin/withdrawals/{w.id}/reject/",
        {"rejection_reason": "invalid card"},
        format="json",
    )
    assert res.status_code == 200
    w.refresh_from_db()
    assert w.status == WithdrawalStatusEnum.REJECTED.value
    normal_user.refresh_from_db()
    # No deduction on reject
    assert normal_user.template_balance == Decimal("500.00")


# ── stats ─────────────────────────────────────────────────────────────────────

def test_dashboard_stats(admin_client, normal_user):
    res = admin_client.get("/api/admin/stats/dashboard/")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "users" in data and "total" in data["users"]
    assert "revenue_30d" in data


# ── audit log read ────────────────────────────────────────────────────────────

def test_audit_log_list(admin_client, normal_user):
    admin_client.patch(
        f"/api/admin/users/{normal_user.id}/ban/", {"is_active": False}, format="json"
    )
    res = admin_client.get("/api/admin/audit-log/")
    assert res.status_code == 200
