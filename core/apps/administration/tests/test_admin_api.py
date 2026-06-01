import pytest
from decimal import Decimal

from rest_framework.test import APIClient

from core.apps.accounts.models import User
from core.apps.administration.models import AdminAuditLogModel
from core.apps.template.models import TemplateModel
from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.enums.template import TemplateSubmissionStatusEnum
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


# ── template submissions: list fields + PATCH ─────────────────────────────────

def _make_submission(user, project):
    """Create a minimal TemplateSubmissionRequestModel for testing."""
    return TemplateSubmissionRequestModel.objects.create(
        user=user,
        project=project,
        name="My Bot Template",
        short_description="Short",
        description="Full description",
        original_price=Decimal("99.00"),
        status=TemplateSubmissionStatusEnum.PENDING.value,
    )


@pytest.fixture
def project(normal_user):
    from core.apps.api.models.project import ProjectModel  # noqa: WPS433
    return ProjectModel.objects.create(name="Test Project", owner=normal_user)


def test_submission_list_includes_required_fields(admin_client, normal_user, project):
    """List endpoint must include id, name, user_phone, project_name, status, created_at."""
    _make_submission(normal_user, project)
    res = admin_client.get("/api/admin/template-submissions/")
    assert res.status_code == 200
    results = res.json().get("data") or res.json().get("results") or res.json()
    # Support both paginated and non-paginated response shapes
    if isinstance(results, dict):
        results = results.get("results", [])
    assert len(results) >= 1
    item = results[0]
    assert "id" in item
    assert "name" in item
    assert item["name"] == "My Bot Template"
    assert "user_phone" in item
    assert item["user_phone"] == normal_user.phone
    assert "project_name" in item
    assert item["project_name"] == "Test Project"
    assert "status" in item
    assert "created_at" in item


def test_submission_list_user_phone_not_null(admin_client, normal_user, project):
    """user_phone must be a real phone string, not None/null."""
    _make_submission(normal_user, project)
    res = admin_client.get("/api/admin/template-submissions/")
    assert res.status_code == 200
    results = res.json().get("data") or res.json().get("results") or res.json()
    if isinstance(results, dict):
        results = results.get("results", [])
    item = results[0]
    assert item["user_phone"] is not None
    assert item["user_phone"] != ""


def test_admin_patch_template_updates_field(admin_client, admin_user):
    """PATCH /api/admin/templates/{id}/ must update editable fields."""
    tpl = TemplateModel.objects.create(
        name="Old Name",
        short_description="s",
        description="d",
        original_price=Decimal("0.00"),
        is_verify=False,
        author=admin_user,
    )
    res = admin_client.patch(
        f"/api/admin/templates/{tpl.id}/",
        {"name": "New Name", "is_verify": True},
        format="json",
    )
    assert res.status_code == 200
    tpl.refresh_from_db()
    assert tpl.name == "New Name"
    assert tpl.is_verify is True


def test_non_admin_cannot_patch_template(user_client, admin_user):
    """Non-admin must receive 403 on template PATCH."""
    tpl = TemplateModel.objects.create(
        name="Tpl",
        short_description="s",
        description="d",
        original_price=Decimal("0.00"),
        author=admin_user,
    )
    res = user_client.patch(f"/api/admin/templates/{tpl.id}/", {"name": "Hacked"}, format="json")
    assert res.status_code == 403


def test_admin_patch_submission_updates_field(admin_client, normal_user, project):
    """PATCH /api/admin/template-submissions/{id}/ must update editable fields."""
    sub = _make_submission(normal_user, project)
    res = admin_client.patch(
        f"/api/admin/template-submissions/{sub.id}/",
        {"name": "Updated Name", "original_price": "199.00"},
        format="json",
    )
    assert res.status_code == 200
    sub.refresh_from_db()
    assert sub.name == "Updated Name"
    assert sub.original_price == Decimal("199.00")


def test_non_admin_cannot_patch_submission(user_client, normal_user, project):
    """Non-admin must receive 403 on submission PATCH."""
    sub = _make_submission(normal_user, project)
    res = user_client.patch(
        f"/api/admin/template-submissions/{sub.id}/",
        {"name": "Hacked"},
        format="json",
    )
    assert res.status_code == 403


def test_submission_approve_creates_template(admin_client, normal_user, project):
    """Approving a submission via the admin API must PUBLISH the actual Template
    (mirrors the Django admin approve action) — previously it only flipped the
    status and no template was created."""
    from core.apps.template.models.template import TemplateModel  # noqa: WPS433

    sub = _make_submission(normal_user, project)
    res = admin_client.patch(
        f"/api/admin/template-submissions/{sub.id}/approve/", {}, format="json"
    )
    assert res.status_code == 200, res.content

    sub.refresh_from_db()
    assert sub.status == TemplateSubmissionStatusEnum.APPROVED.value
    assert sub.template is not None
    assert TemplateModel.objects.filter(id=sub.template.id).exists()
    # Template fields are copied from the submission.
    assert sub.template.name == sub.name
    assert sub.template.author == sub.user
    assert sub.template.is_verify is True


def test_submission_approve_is_idempotent_no_duplicate_template(admin_client, normal_user, project):
    """A second approve must NOT create a second template."""
    from core.apps.template.models.template import TemplateModel  # noqa: WPS433

    sub = _make_submission(normal_user, project)
    admin_client.patch(f"/api/admin/template-submissions/{sub.id}/approve/", {}, format="json")
    sub.refresh_from_db()
    first_template_id = sub.template.id
    count_after_first = TemplateModel.objects.count()

    admin_client.patch(f"/api/admin/template-submissions/{sub.id}/approve/", {}, format="json")
    sub.refresh_from_db()
    assert sub.template.id == first_template_id
    assert TemplateModel.objects.count() == count_after_first  # no duplicate


def test_submission_reject_creates_no_template(admin_client, normal_user, project):
    """Rejecting must not create a template."""
    from core.apps.template.models.template import TemplateModel  # noqa: WPS433

    sub = _make_submission(normal_user, project)
    before = TemplateModel.objects.count()
    res = admin_client.patch(
        f"/api/admin/template-submissions/{sub.id}/reject/", {}, format="json"
    )
    assert res.status_code == 200
    sub.refresh_from_db()
    assert sub.status == TemplateSubmissionStatusEnum.REJECTED.value
    assert sub.template is None
    assert TemplateModel.objects.count() == before


# ── settings: list + upsert ───────────────────────────────────────────────────

def test_settings_list_empty(admin_client, db):
    """GET /api/admin/settings/ returns an empty list when no rows exist."""
    res = admin_client.get("/api/admin/settings/")
    assert res.status_code == 200
    data = res.json()["data"]
    assert isinstance(data, list)


def test_settings_list_with_data(admin_client, db):
    """GET returns all SettingsModel groups with their options."""
    from core.apps.shared.models.settings import OptionsModel, SettingsModel  # noqa: WPS433

    s = SettingsModel.objects.create(key="engine", is_public=False, description="Engine settings")
    OptionsModel.objects.create(settings=s, key="version", value=["3.5.11-prod"])

    res = admin_client.get("/api/admin/settings/")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 1
    engine_group = next((g for g in data if g["key"] == "engine"), None)
    assert engine_group is not None
    assert engine_group["is_public"] is False
    assert len(engine_group["options"]) == 1
    assert engine_group["options"][0]["key"] == "version"
    assert engine_group["options"][0]["value"] == ["3.5.11-prod"]


def test_settings_set_creates_new(admin_client, db):
    """POST /api/admin/settings/set/ creates SettingsModel + OptionsModel when absent."""
    res = admin_client.post(
        "/api/admin/settings/set/",
        {"settings_key": "engine", "option_key": "version", "value": ["3.6.0-prod"]},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["key"] == "version"
    assert data["value"] == ["3.6.0-prod"]

    from core.apps.shared.models.settings import OptionsModel, SettingsModel  # noqa: WPS433

    s = SettingsModel.objects.get(key="engine")
    opt = OptionsModel.objects.get(settings=s, key="version")
    assert opt.value == ["3.6.0-prod"]


def test_settings_set_updates_existing(admin_client, db):
    """POST /api/admin/settings/set/ updates value when option already exists."""
    from core.apps.shared.models.settings import OptionsModel, SettingsModel  # noqa: WPS433

    s = SettingsModel.objects.create(key="currency", is_public=True)
    OptionsModel.objects.create(settings=s, key="exchange_rate", value=["12500"])

    res = admin_client.post(
        "/api/admin/settings/set/",
        {"settings_key": "currency", "option_key": "exchange_rate", "value": ["13000"]},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["data"]["value"] == ["13000"]
    assert OptionsModel.objects.filter(settings=s, key="exchange_rate").count() == 1


def test_settings_set_writes_audit_log(admin_client, db):
    """POST /api/admin/settings/set/ must write an audit log entry."""
    admin_client.post(
        "/api/admin/settings/set/",
        {"settings_key": "engine", "option_key": "version", "value": ["3.7.0-prod"]},
        format="json",
    )
    assert AdminAuditLogModel.objects.filter(action="settings.set").exists()


def test_settings_set_invalid_empty_list(admin_client, db):
    """POST with empty value list must return 400."""
    res = admin_client.post(
        "/api/admin/settings/set/",
        {"settings_key": "engine", "option_key": "version", "value": []},
        format="json",
    )
    assert res.status_code == 400


def test_settings_set_forbidden_for_non_admin(user_client, db):
    """Non-admin must receive 403 on settings set."""
    res = user_client.post(
        "/api/admin/settings/set/",
        {"settings_key": "engine", "option_key": "version", "value": ["3.6.0-prod"]},
        format="json",
    )
    assert res.status_code == 403
