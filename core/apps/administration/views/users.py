# type: ignore
"""Admin Users endpoints. List + retrieve + ban + balance edit."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import BigIntegerField, F, Q, Value
from django.db.models.functions import Coalesce
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.users import (
    AdminUserBalanceSerializer,
    AdminUserBanSerializer,
    AdminUserSerializer,
)
from core.apps.administration.services import log_admin_action

User = get_user_model()


class AdminUsersView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = (
            User.objects.all()
            .select_related("subscription", "subscription__plan")
            .annotate(
                tokens_used_total=Coalesce(
                    F("subscription__tokens_used_input") + F("subscription__tokens_used_output"),
                    Value(0),
                    output_field=BigIntegerField(),
                )
            )
            .order_by("-id")
        )
        p = self.request.query_params
        search = p.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(phone__icontains=search)
                | Q(email__icontains=search)
                | Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        role = p.get("role", "").strip()
        if role:
            qs = qs.filter(role=role)
        is_active = p.get("is_active", "").strip()
        if is_active in ("true", "false"):
            qs = qs.filter(is_active=(is_active == "true"))
        is_staff = p.get("is_staff", "").strip()
        if is_staff in ("true", "false"):
            qs = qs.filter(is_staff=(is_staff == "true"))
        plan = p.get("plan", "").strip()
        if plan:
            qs = qs.filter(subscription__plan__name=plan)
        # Joined date range (YYYY-MM-DD)
        joined_after = p.get("joined_after", "").strip()
        if joined_after:
            qs = qs.filter(date_joined__date__gte=joined_after)
        joined_before = p.get("joined_before", "").strip()
        if joined_before:
            qs = qs.filter(date_joined__date__lte=joined_before)
        # Balance range
        bal_min = p.get("balance_min", "").strip()
        if bal_min.lstrip("-").isdigit():
            qs = qs.filter(balance__gte=int(bal_min))
        bal_max = p.get("balance_max", "").strip()
        if bal_max.lstrip("-").isdigit():
            qs = qs.filter(balance__lte=int(bal_max))
        # Sort
        ordering = p.get("ordering", "").strip()
        if ordering in (
            "id", "-id",
            "balance", "-balance",
            "date_joined", "-date_joined",
            "tokens_used_total", "-tokens_used_total",
        ):
            qs = qs.order_by(ordering)
        return qs

    def retrieve(self, request, *args, **kwargs):
        """Rich detail: profile + subscription/tokens + projects +
        purchased & authored templates + balances."""
        from core.apps.api.models.project import ProjectModel  # noqa: WPS433
        from core.apps.template.models import (  # noqa: WPS433
            TemplateModel,
            TemplateOrderModel,
        )

        u = self.get_object()

        sub = getattr(u, "subscription", None)
        subscription = None
        if sub is not None:
            plan = sub.plan
            subscription = {
                "plan": plan.get_name_display() if hasattr(plan, "get_name_display") else str(plan.name),
                "plan_name": plan.name,
                "status": sub.status,
                "started_at": sub.started_at,
                "expires_at": sub.expires_at,
                "token_reset_at": sub.token_reset_at,
                "bots_count": sub.bots_count,
                "tokens_used_input": sub.tokens_used_input,
                "tokens_used_output": sub.tokens_used_output,
                "tokens_used_total": sub.tokens_used_input + sub.tokens_used_output,
                "token_limit": plan.max_tokens,
                "max_bots": plan.max_bots,
            }

        projects = [
            {
                "id": pr.id,
                "name": pr.name,
                "username": pr.username,
                "is_template": pr.is_template,
                "created_at": pr.created_at,
            }
            for pr in ProjectModel.objects.filter(owner=u).order_by("-id")[:200]
        ]

        purchased = [
            {
                "id": o.id,
                "template_id": o.template_id,
                "template_name": getattr(o.template, "name", None),
                "amount": str(o.amount),
                "status": o.status,
                "payment_status": o.payment_status,
                "created_at": o.created_at,
            }
            for o in TemplateOrderModel.objects.filter(user=u).select_related("template").order_by("-id")[:200]
        ]

        authored = [
            {
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "is_verify": t.is_verify,
                "views": t.views,
                "original_price": str(t.original_price),
                "created_at": t.created_at,
            }
            for t in TemplateModel.objects.filter(author=u).order_by("-id")[:200]
        ]

        data = {
            "id": u.id,
            "phone": u.phone,
            "email": u.email,
            "username": u.username,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": u.role,
            "is_active": u.is_active,
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
            "date_joined": u.date_joined,
            "validated_at": u.validated_at,
            "balance": u.balance,
            "template_balance": str(u.template_balance),
            "subscription": subscription,
            "projects": projects,
            "projects_count": len(projects),
            "purchased_templates": purchased,
            "purchased_count": len(purchased),
            "authored_templates": authored,
            "authored_count": len(authored),
        }
        return Response(data)

    @action(detail=True, methods=["patch"])
    def ban(self, request, pk=None):
        target = self.get_object()
        serializer = AdminUserBanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        before = {"is_active": target.is_active}
        target.is_active = serializer.validated_data["is_active"]
        target.save(update_fields=["is_active", "updated_at"])
        log_admin_action(
            actor=request.user,
            action="user.set_active",
            target=target,
            before=before,
            after={"is_active": target.is_active},
            note=serializer.validated_data.get("note", "")[:255],
            request=request,
        )
        return Response(self.get_serializer(target).data)

    @action(detail=True, methods=["patch"])
    def balance(self, request, pk=None):
        target = self.get_object()
        serializer = AdminUserBalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        field = serializer.validated_data["field"]
        value = serializer.validated_data["value"]
        before = {field: str(getattr(target, field))}
        if field == "balance":
            target.balance = int(value)
        else:
            target.template_balance = Decimal(value)
        target.save(update_fields=[field, "updated_at"])
        log_admin_action(
            actor=request.user,
            action=f"user.{field}.set",
            target=target,
            before=before,
            after={field: str(getattr(target, field))},
            note=serializer.validated_data.get("note", "")[:255],
            request=request,
        )
        return Response(self.get_serializer(target).data)
