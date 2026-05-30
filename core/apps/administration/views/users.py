# type: ignore
"""Admin Users endpoints. List + retrieve + ban + balance edit."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q
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
        qs = User.objects.all().order_by("-id")
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(phone__icontains=search)
                | Q(email__icontains=search)
                | Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        role = self.request.query_params.get("role", "").strip()
        if role:
            qs = qs.filter(role=role)
        is_active = self.request.query_params.get("is_active", "").strip()
        if is_active in ("true", "false"):
            qs = qs.filter(is_active=(is_active == "true"))
        return qs

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
