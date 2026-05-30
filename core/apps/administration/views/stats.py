# type: ignore
"""GET /api/v1/admin/stats/dashboard — KPIs for the admin landing page.

Returns:
- users_total, users_active, users_new_7d, users_new_30d
- projects_total, projects_with_release
- templates_total, templates_pending_verify
- withdrawals_pending
- revenue_30d (from confirmed orders)
- daily_signups (last 30 days, for chart)
- daily_orders (last 30 days)
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser

User = get_user_model()


def _daily_buckets(qs, date_field: str, days: int = 30) -> list[dict]:
    since = timezone.now() - timedelta(days=days)
    rows = (
        qs.filter(**{f"{date_field}__gte": since})
        .annotate(day=TruncDate(date_field))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    return [{"day": r["day"].isoformat(), "count": r["count"]} for r in rows]


@api_view(["GET"])
@permission_classes([IsAdminUser])
def dashboard_stats(request):
    from core.apps.api.models.project import ProjectModel, RelaseModel  # noqa: WPS433
    from core.apps.template.models import (  # noqa: WPS433
        TemplateModel,
        TemplateOrderModel,
        TemplateWithdrawalRequestModel,
    )
    from core.apps.template.enums.order import TemplateOrderStatusEnum  # noqa: WPS433
    from core.apps.template.enums.withdrawal import (  # noqa: WPS433
        TemplateWithdrawalRequestStatusEnum,
    )

    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    users_total = User.objects.count()
    users_active = User.objects.filter(is_active=True).count()
    users_new_7d = User.objects.filter(date_joined__gte=week_ago).count()
    users_new_30d = User.objects.filter(date_joined__gte=month_ago).count()

    projects_total = ProjectModel.objects.count()
    projects_with_release = (
        RelaseModel.objects.values("project_id").distinct().count()
    )

    templates_total = TemplateModel.objects.count()
    templates_pending_verify = TemplateModel.objects.filter(is_verify=False).count()

    withdrawals_pending = TemplateWithdrawalRequestModel.objects.filter(
        status=TemplateWithdrawalRequestStatusEnum.PENDING.value,
    ).count()

    revenue_30d = (
        TemplateOrderModel.objects.filter(
            payment_status=True,
            status=TemplateOrderStatusEnum.CONFIRM.value,
            created_at__gte=month_ago,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    return Response(
        {
            "users": {
                "total": users_total,
                "active": users_active,
                "new_7d": users_new_7d,
                "new_30d": users_new_30d,
            },
            "projects": {
                "total": projects_total,
                "with_release": projects_with_release,
            },
            "templates": {
                "total": templates_total,
                "pending_verify": templates_pending_verify,
            },
            "withdrawals": {"pending": withdrawals_pending},
            "revenue_30d": str(revenue_30d),
            "daily_signups": _daily_buckets(User.objects, "date_joined"),
            "daily_orders": _daily_buckets(
                TemplateOrderModel.objects.filter(payment_status=True),
                "created_at",
            ),
        }
    )
