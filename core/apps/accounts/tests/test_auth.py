from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django_core.models import SmsConfirm
from pydantic import BaseModel
from rest_framework import status
from rest_framework.test import APIClient

from core.apps.api.enums.plan import PlanStatus, PlanType
from core.apps.api.models import PlanModel
from core.apps.api.models.plan import UserSubscription
from core.apps.accounts.models import ResetToken
from core.services import SmsService


class TokenModel(BaseModel):
    access: str
    refresh: str


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    phone = "998999999999"
    password = "password"
    user = get_user_model().objects.create_user(phone=phone, first_name="John", last_name="Doe", password=password)
    return user


@pytest.fixture
def sms_code(test_user):
    code = "1111"
    SmsConfirm.objects.create(phone=test_user.phone, code=code)
    return code


@pytest.mark.django_db
def test_reg_view(api_client):
    data = {
        "phone": "998999999991",
        "first_name": "John",
        "last_name": "Doe",
        "password": "password",
    }
    with patch.object(SmsService, "send_confirm", return_value=True):
        response = api_client.post(reverse("auth-register"), data=data)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.data["data"]["detail"] == f"Sms {data['phone']} raqamiga yuborildi"


@pytest.mark.django_db
def test_confirm_view(api_client, test_user, sms_code):
    data = {"phone": test_user.phone, "code": sms_code}
    response = api_client.post(reverse("auth-confirm"), data=data)
    assert response.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.django_db
def test_invalid_confirm_view(api_client, test_user):
    data = {"phone": test_user.phone, "code": "1112"}
    response = api_client.post(reverse("auth-confirm"), data=data)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_reset_confirmation_code_view(api_client, test_user, sms_code):
    data = {"phone": test_user.phone, "code": sms_code}
    response = api_client.post(reverse("auth-confirm"), data=data)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "token" in response.data["data"]


@pytest.mark.django_db
def test_reset_confirmation_code_view_invalid_code(api_client, test_user):
    data = {"phone": test_user.phone, "code": "123456"}
    response = api_client.post(reverse("auth-confirm"), data=data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_reset_set_password_view(api_client, test_user):
    token = ResetToken.objects.create(user=test_user, token="token")
    data = {"token": token.token, "password": "new_password"}
    response = api_client.post(reverse("reset-password-reset-password-set"), data=data)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_reset_set_password_view_invalid_token(api_client):
    token = "test_token"
    data = {"token": token, "password": "new_password"}
    with patch.object(get_user_model().objects, "filter", return_value=get_user_model().objects.none()):
        response = api_client.post(reverse("reset-password-reset-password-set"), data=data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["data"]["detail"] == "Invalid token"


@pytest.mark.django_db
def test_resend_view(api_client, test_user):
    data = {"phone": test_user.phone}
    response = api_client.post(reverse("auth-resend"), data=data)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_reset_password_view(api_client, test_user):
    data = {"phone": test_user.phone}
    response = api_client.post(reverse("reset-password-reset-password"), data=data)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_me_view(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    response = api_client.get(reverse("me-me"))
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_me_view_returns_ai_token_usage_for_existing_subscription(api_client, test_user):
    plan = PlanModel.objects.create(
        name=PlanType.PRO,
        max_input_tokens=1000,
        max_output_tokens=400,
    )
    UserSubscription.objects.create(
        user=test_user,
        plan=plan,
        status=PlanStatus.ACTIVE,
        tokens_used_input=250,
        tokens_used_output=150,
    )

    api_client.force_authenticate(user=test_user)
    response = api_client.get(reverse("me-me"))
    assert response.status_code == status.HTTP_200_OK

    payload = response.data.get("data", response.data)
    usage = payload["ai_token_usage"]
    assert usage["limit"] == 1400
    assert usage["used"] == 400
    assert usage["remaining"] == 1000
    assert usage["input_used"] == 250
    assert usage["output_used"] == 150
    assert usage["plan"]["name"] == PlanType.PRO
    assert usage["plan"]["display"] == "Pro"
    assert usage["status"] == PlanStatus.ACTIVE
    assert usage["token_reset_at"] is not None


@pytest.mark.django_db
def test_me_view_creates_free_subscription_when_missing(api_client, test_user):
    PlanModel.objects.get_or_create(
        name=PlanType.FREE,
        defaults={"max_input_tokens": 100, "max_output_tokens": 50},
    )

    api_client.force_authenticate(user=test_user)
    response = api_client.get(reverse("me-me"))
    assert response.status_code == status.HTTP_200_OK
    assert UserSubscription.objects.filter(user=test_user).exists()

    payload = response.data.get("data", response.data)
    usage = payload["ai_token_usage"]
    assert usage["plan"]["name"] == PlanType.FREE
    assert usage["plan"]["display"] == "Free"


@pytest.mark.django_db
def test_me_update_view(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    data = {"first_name": "Updated"}
    response = api_client.patch(reverse("me-user-update"), data=data)
    assert response.status_code == status.HTTP_200_OK
