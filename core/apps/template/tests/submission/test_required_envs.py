"""Tests for required_envs feature on template submissions and create_from_template."""
import json
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.accounts.models import User
from core.apps.api.models import ProjectModel
from core.apps.api.models.project import EnviromentModel
from core.apps.template.enums.template import TemplateSubmissionStatusEnum
from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.models.template import TemplateModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(phone="+998900000001", username="reqenv_user", password="pass")


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        phone="+998900000002",
        username="reqenv_admin",
        password="pass",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def project_no_env(db, user):
    """Project whose flow does NOT reference any env vars."""
    return ProjectModel.objects.create(
        name="No-env project",
        owner=user,
        flow={"nodes": [{"data": {"text": "hello"}}], "edges": []},
    )


@pytest.fixture
def project_with_env(db, user):
    """Project whose flow references {{env.ADMIN_CHAT_ID}}."""
    return ProjectModel.objects.create(
        name="Env project",
        owner=user,
        flow={"nodes": [{"data": {"text": "notify {{env.ADMIN_CHAT_ID}}"}}], "edges": []},
    )


@pytest.fixture
def project_multi_env(db, user):
    """Project whose flow references ADMIN_CHAT_ID and SUPPORT_PHONE."""
    return ProjectModel.objects.create(
        name="Multi-env project",
        owner=user,
        flow={
            "nodes": [
                {"data": {"text": "{{env.ADMIN_CHAT_ID}} / {{env.SUPPORT_PHONE}}"}},
            ],
            "edges": [],
        },
    )


@pytest.fixture
def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---------------------------------------------------------------------------
# (a) Submission without required_envs → 400
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_submission_without_required_envs_returns_400(auth_client, project_no_env):
    """Sending a submission without required_envs field must return 400."""
    url = reverse("submission-list")
    data = {
        "project": project_no_env.id,
        "name": "Missing field template",
        "short_description": "short",
        "description": "long",
        "original_price": "100.00",
        # required_envs intentionally omitted
    }
    response = auth_client.post(url, data=data)
    assert response.status_code == 400, response.json()


@pytest.mark.django_db
def test_submission_with_empty_required_envs_accepted(auth_client, project_no_env):
    """Flow with no env refs accepts required_envs=[]."""
    url = reverse("submission-list")
    data = {
        "project": project_no_env.id,
        "name": "Empty envs template",
        "short_description": "short",
        "description": "long",
        "original_price": "100.00",
        "required_envs": json.dumps([]),
    }
    response = auth_client.post(url, data=data)
    assert response.status_code == 201, response.json()
    obj = TemplateSubmissionRequestModel.objects.get(name="Empty envs template")
    assert obj.required_envs == []


# ---------------------------------------------------------------------------
# (b) Flow has {{env.X}} but X not declared → 400 with key listed
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_submission_undeclared_flow_env_returns_400(auth_client, project_with_env):
    """Flow uses {{env.ADMIN_CHAT_ID}} but required_envs=[] → 400."""
    url = reverse("submission-list")
    data = {
        "project": project_with_env.id,
        "name": "Missing decl template",
        "short_description": "short",
        "description": "long",
        "original_price": "100.00",
        "required_envs": json.dumps([]),
    }
    response = auth_client.post(url, data=data)
    assert response.status_code == 400, response.json()
    body = response.json()
    # Error should mention ADMIN_CHAT_ID
    error_text = str(body)
    assert "ADMIN_CHAT_ID" in error_text


@pytest.mark.django_db
def test_submission_partial_undeclared_returns_400_with_missing_key(auth_client, project_multi_env):
    """Only ADMIN_CHAT_ID declared but SUPPORT_PHONE also used → 400 mentioning SUPPORT_PHONE."""
    url = reverse("submission-list")
    data = {
        "project": project_multi_env.id,
        "name": "Partial decl template",
        "short_description": "short",
        "description": "long",
        "original_price": "100.00",
        "required_envs": json.dumps([{"key": "ADMIN_CHAT_ID", "description": "Admin chat"}]),
    }
    response = auth_client.post(url, data=data)
    assert response.status_code == 400, response.json()
    assert "SUPPORT_PHONE" in str(response.json())


@pytest.mark.django_db
def test_submission_all_envs_declared_accepted(auth_client, project_multi_env):
    """All env keys declared → 201."""
    url = reverse("submission-list")
    data = {
        "project": project_multi_env.id,
        "name": "Full decl template",
        "short_description": "short",
        "description": "long",
        "original_price": "100.00",
        "required_envs": json.dumps(
            [
                {"key": "ADMIN_CHAT_ID", "description": "Admin"},
                {"key": "SUPPORT_PHONE", "description": "Support"},
            ]
        ),
    }
    response = auth_client.post(url, data=data)
    assert response.status_code == 201, response.json()
    obj = TemplateSubmissionRequestModel.objects.get(name="Full decl template")
    assert len(obj.required_envs) == 2


# ---------------------------------------------------------------------------
# (c) Approve → template.required_envs copied from submission
# ---------------------------------------------------------------------------


@pytest.fixture
def pending_submission_with_envs(db, user, project_with_env):
    return TemplateSubmissionRequestModel.objects.create(
        user=user,
        project=project_with_env,
        name="Approvable template",
        short_description="short",
        description="long",
        original_price=Decimal("99.00"),
        status=TemplateSubmissionStatusEnum.PENDING.value,
        required_envs=[{"key": "ADMIN_CHAT_ID", "description": "Admin chat ID"}],
    )


@pytest.mark.django_db
def test_approve_copies_required_envs_to_template(admin_user, pending_submission_with_envs):
    """When a submission is approved via admin action, required_envs must be copied to the template."""
    from django.contrib.admin.sites import AdminSite

    from core.apps.template.admin.submission import TemplateSubmissionRequestAdmin

    site = AdminSite()
    admin = TemplateSubmissionRequestAdmin(TemplateSubmissionRequestModel, site)

    from django.contrib.messages.storage.fallback import FallbackStorage

    class MockRequest:
        user = admin_user
        session = {}

    request = MockRequest()
    request._messages = FallbackStorage(request)

    submission = pending_submission_with_envs
    # Simulate approve action (bulk action)
    admin.approve_submissions(request, TemplateSubmissionRequestModel.objects.filter(pk=submission.pk))

    submission.refresh_from_db()
    assert submission.template is not None
    template = submission.template
    assert template.required_envs == [{"key": "ADMIN_CHAT_ID", "description": "Admin chat ID"}]


# ---------------------------------------------------------------------------
# (d) create_from_template: missing envs → 400
# ---------------------------------------------------------------------------


@pytest.fixture
def template_with_required_envs(db, user, project_with_env):
    """A verified template that requires ADMIN_CHAT_ID."""
    t = TemplateModel.objects.create(
        author=user,
        name="Env-required template",
        image="template/fake.png",
        project=project_with_env,
        short_description="short",
        description="long",
        original_price=Decimal("0.00"),
        is_verify=True,
        required_envs=[{"key": "ADMIN_CHAT_ID", "description": "Admin chat"}],
    )
    return t


@pytest.fixture
def template_no_required_envs(db, user, project_no_env):
    """A verified template with no required envs (backward compat)."""
    t = TemplateModel.objects.create(
        author=user,
        name="No-env template",
        image="template/fake.png",
        project=project_no_env,
        short_description="short",
        description="long",
        original_price=Decimal("0.00"),
        is_verify=True,
        required_envs=[],
    )
    return t


@pytest.mark.django_db
@patch("core.apps.api.views.project.set_webhook")
@patch("core.apps.api.views.project.copy_collections")
def test_create_from_template_missing_envs_returns_400(_cc, _sw, auth_client, template_with_required_envs, user):
    """Calling create_from_template without ADMIN_CHAT_ID → 400 with key listed."""
    from core.apps.template.models.order import TemplateOrderModel

    TemplateOrderModel.objects.create(
        user=user,
        template=template_with_required_envs,
        payment_status=True,
        status="confirm",
        amount=Decimal("0.00"),
    )
    url = reverse("project-create-from-template")
    data = {
        "template": template_with_required_envs.id,
        "name": "My new bot",
        "token": "123:tok",
        # envs intentionally empty/missing
    }
    response = auth_client.post(url, data=data, format="json")
    assert response.status_code == 400, response.json()
    error_text = str(response.json())
    assert "ADMIN_CHAT_ID" in error_text


@pytest.mark.django_db
@patch("core.apps.api.signals.project.sync_bot")
@patch("core.apps.api.signals.project.deploy_service")
@patch("core.apps.api.views.project.set_webhook")
@patch("core.apps.api.views.project.copy_collections")
def test_create_from_template_with_envs_creates_env_models(_cc, _sw, _ds, _sb, auth_client, template_with_required_envs, user):
    """Providing all required envs → 200 and EnviromentModel records created."""
    _ds.return_value.metadata.name = "release-test-svc"
    from core.apps.template.models.order import TemplateOrderModel

    TemplateOrderModel.objects.create(
        user=user,
        template=template_with_required_envs,
        payment_status=True,
        status="confirm",
        amount=Decimal("0.00"),
    )
    url = reverse("project-create-from-template")
    data = {
        "template": template_with_required_envs.id,
        "name": "My bot with envs",
        "token": "123:tok",
        "envs": {"ADMIN_CHAT_ID": "-1001234567890"},
    }
    response = auth_client.post(url, data=data, format="json")
    assert response.status_code == 200, response.json()
    project = ProjectModel.objects.get(name="My bot with envs")
    assert EnviromentModel.objects.filter(project=project, key="ADMIN_CHAT_ID").exists()
    env = EnviromentModel.objects.get(project=project, key="ADMIN_CHAT_ID")
    assert env.value == "-1001234567890"


# ---------------------------------------------------------------------------
# (e) Backward compat: template with no required_envs still works
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@patch("core.apps.api.signals.project.sync_bot")
@patch("core.apps.api.signals.project.deploy_service")
@patch("core.apps.api.views.project.set_webhook")
@patch("core.apps.api.views.project.copy_collections")
def test_create_from_template_no_required_envs_backward_compat(_cc, _sw, _ds, _sb, auth_client, template_no_required_envs, user):
    """Templates with empty required_envs work without providing envs (backward compat)."""
    _ds.return_value.metadata.name = "release-test-svc"
    from core.apps.template.models.order import TemplateOrderModel

    TemplateOrderModel.objects.create(
        user=user,
        template=template_no_required_envs,
        payment_status=True,
        status="confirm",
        amount=Decimal("0.00"),
    )
    url = reverse("project-create-from-template")
    data = {
        "template": template_no_required_envs.id,
        "name": "Old bot compat",
        "token": "123:tok",
    }
    response = auth_client.post(url, data=data, format="json")
    assert response.status_code == 200, response.json()


# ---------------------------------------------------------------------------
# Validator unit tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value, expect_error",
    [
        ([], False),
        ([{"key": "ADMIN_CHAT_ID"}], False),
        ([{"key": "ADMIN_CHAT_ID", "description": "desc"}], False),
        ([{"key": "RELEASE_BOT_TOKEN"}], True),  # reserved
        ([{"key": "lowercase"}], True),  # lowercase not allowed
        ([{"key": "VALID"}, {"key": "VALID"}], True),  # duplicate
        ([{"key": "1INVALID"}], True),  # starts with digit
        ("[]", False),  # JSON string accepted
        ('[{"key": "OK"}]', False),
    ],
)
def test_validate_required_envs_unit(value, expect_error):
    from rest_framework.exceptions import ValidationError

    from core.apps.template.validators.template import validate_required_envs

    if expect_error:
        with pytest.raises(ValidationError):
            validate_required_envs(value)
    else:
        result = validate_required_envs(value)
        assert isinstance(result, list)
