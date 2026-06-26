# type: ignore
"""
POST /api/subscription/usage/report/ uchun testlar.

Asosiy tekshiruv: cache_read_tokens bilan billable_input = uncached + round(cache_read * rate).
"""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.models.plan import PlanModel, UserSubscription
from core.apps.api.enums.plan import PlanType


REPORT_URL = "subscription-usage-report"


def _internal_client(user_id=None):
    client = APIClient()
    headers = {"HTTP_X_INTERNAL_TOKEN": settings.INTERNAL_API_TOKEN}
    if user_id is not None:
        headers["HTTP_X_USER_ID"] = str(user_id)
    client.credentials(**headers)
    return client


def _make_plan(rate=Decimal("0.10"), max_tokens=10_000_000):
    plan, _ = PlanModel.objects.get_or_create(
        name=PlanType.FREE,
        defaults={
            "price": Decimal("0.00"),
            "max_tokens": max_tokens,
            "max_bots": 1,
            "cached_token_rate": rate,
        },
    )
    plan.cached_token_rate = rate
    plan.save(update_fields=["cached_token_rate"])
    return plan


@pytest.fixture(autouse=True)
def _patch_metrics():
    with patch("core.apps.shared.observability.metrics.safe_inc"):
        yield


@pytest.mark.django_db
class TestReportUsageCachedTokens:

    def _post(self, payload, client=None, user_id=None):
        c = client or _internal_client(user_id=user_id or payload.get("user_id"))
        url = reverse(REPORT_URL)
        return c.post(url, data=payload, format="json")

    def _subscription(self, user, plan):
        sub, _ = UserSubscription.objects.get_or_create(user=user, defaults={"plan": plan})
        if sub.plan_id != plan.pk:
            sub.plan = plan
            sub.save(update_fields=["plan"])
        return sub

    def test_cache_discount_applied(self):
        """
        input_tokens=1000, cache_read_tokens=900, rate=0.10
        → billable_input = (1000-900) + round(900*0.10) = 100 + 90 = 190
        """
        plan = _make_plan(rate=Decimal("0.10"))
        sub = UserSubscription._create_fake()
        sub.plan = plan
        sub.tokens_used_input = 0
        sub.save(update_fields=["plan", "tokens_used_input"])

        settings.INTERNAL_API_TOKEN = "test-secret"

        resp = self._post(
            {
                "user_id": sub.user_id,
                "input_tokens": 1000,
                "output_tokens": 50,
                "cache_read_tokens": 900,
            }
        )
        assert resp.status_code == 200, resp.data

        sub.refresh_from_db()
        assert sub.tokens_used_input == 190, f"Expected 190, got {sub.tokens_used_input}"
        assert sub.tokens_used_output == 50

    def test_no_cache_read_tokens_behaves_as_before(self):
        """cache_read_tokens o'tkazilmasa, to'liq input_tokens hisoblanishi kerak."""
        plan = _make_plan(rate=Decimal("0.10"))
        sub = UserSubscription._create_fake()
        sub.plan = plan
        sub.tokens_used_input = 0
        sub.save(update_fields=["plan", "tokens_used_input"])

        settings.INTERNAL_API_TOKEN = "test-secret"

        resp = self._post(
            {
                "user_id": sub.user_id,
                "input_tokens": 500,
                "output_tokens": 100,
            }
        )
        assert resp.status_code == 200, resp.data

        sub.refresh_from_db()
        assert sub.tokens_used_input == 500
        assert sub.tokens_used_output == 100

    def test_cache_read_clamped_to_input(self):
        """cache_read_tokens > input_tokens bo'lsa, input_tokens gacha qisqartirilishi kerak."""
        plan = _make_plan(rate=Decimal("0.10"))
        sub = UserSubscription._create_fake()
        sub.plan = plan
        sub.tokens_used_input = 0
        sub.save(update_fields=["plan", "tokens_used_input"])

        settings.INTERNAL_API_TOKEN = "test-secret"

        resp = self._post(
            {
                "user_id": sub.user_id,
                "input_tokens": 200,
                "output_tokens": 0,
                "cache_read_tokens": 9999,  # input dan oshadi
            }
        )
        assert resp.status_code == 200, resp.data

        sub.refresh_from_db()
        # cache_read clamped to 200 → uncached=0, billable = round(200*0.10) = 20
        assert sub.tokens_used_input == 20

    def test_full_rate_plan(self):
        """rate=1.00 bo'lsa, kesh chegirmasi yo'q — to'liq hisoblanadi."""
        plan = _make_plan(rate=Decimal("1.00"))
        sub = UserSubscription._create_fake()
        sub.plan = plan
        sub.tokens_used_input = 0
        sub.save(update_fields=["plan", "tokens_used_input"])

        settings.INTERNAL_API_TOKEN = "test-secret"

        resp = self._post(
            {
                "user_id": sub.user_id,
                "input_tokens": 1000,
                "output_tokens": 0,
                "cache_read_tokens": 900,
            }
        )
        assert resp.status_code == 200, resp.data

        sub.refresh_from_db()
        # uncached=100, cached=round(900*1.00)=900 → 1000
        assert sub.tokens_used_input == 1000

    def test_zero_rate_plan(self):
        """rate=0.00 bo'lsa, kesh tokenlari bepul."""
        plan = _make_plan(rate=Decimal("0.00"))
        sub = UserSubscription._create_fake()
        sub.plan = plan
        sub.tokens_used_input = 0
        sub.save(update_fields=["plan", "tokens_used_input"])

        settings.INTERNAL_API_TOKEN = "test-secret"

        resp = self._post(
            {
                "user_id": sub.user_id,
                "input_tokens": 1000,
                "output_tokens": 0,
                "cache_read_tokens": 900,
            }
        )
        assert resp.status_code == 200, resp.data

        sub.refresh_from_db()
        # uncached=100, cached=0 → 100
        assert sub.tokens_used_input == 100

    def test_unauthorized_request_returns_403(self):
        # Noto'g'ri token — InternalTokenAuthentication o'tib ketadi (None), lekin
        # view ichidagi manual tekshiruv 403 qaytaradi.
        plan = _make_plan()
        sub = UserSubscription._create_fake()
        sub.plan = plan
        sub.save(update_fields=["plan"])

        settings.INTERNAL_API_TOKEN = "test-secret"
        client = APIClient()
        # wrong token + user-id berish kerak (auth o'tmaydi, view o'z tekshiruvini qiladi)
        client.credentials(HTTP_X_INTERNAL_TOKEN="wrong-token", HTTP_X_USER_ID=str(sub.user_id))

        resp = client.post(
            reverse(REPORT_URL),
            data={"user_id": sub.user_id, "input_tokens": 10, "output_tokens": 5},
            format="json",
        )
        assert resp.status_code == 403

    def test_response_contains_billable_input(self):
        """Javob 'input_tokens_added' da billable_input qiymatini qaytaradi."""
        plan = _make_plan(rate=Decimal("0.10"))
        sub = UserSubscription._create_fake()
        sub.plan = plan
        sub.save(update_fields=["plan"])

        settings.INTERNAL_API_TOKEN = "test-secret"

        resp = self._post(
            {
                "user_id": sub.user_id,
                "input_tokens": 1000,
                "output_tokens": 0,
                "cache_read_tokens": 900,
            }
        )
        assert resp.status_code == 200, resp.data
        assert resp.data["data"]["input_tokens_added"] == 190
