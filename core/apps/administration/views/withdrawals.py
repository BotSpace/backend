# type: ignore
"""Admin Withdrawals — approve/reject with atomic balance deduction."""

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.withdrawals import (
    AdminWithdrawalApproveSerializer,
    AdminWithdrawalRejectSerializer,
    AdminWithdrawalSerializer,
)
from core.apps.administration.services import log_admin_action
from core.apps.template.enums.withdrawal import WithdrawalStatusEnum
from core.apps.template.models.withdrawal import TemplateWithdrawalRequestModel


class AdminWithdrawalsView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminWithdrawalSerializer

    def get_queryset(self):
        qs = (
            TemplateWithdrawalRequestModel.objects
            .select_related("user", "reviewed_by")
            .order_by("-id")
        )
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        serializer = AdminWithdrawalApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            target = (
                TemplateWithdrawalRequestModel.objects
                .select_for_update()
                .select_related("user")
                .get(pk=pk)
            )
            if target.status != WithdrawalStatusEnum.PENDING.value:
                return Response(
                    {"detail": f"Withdrawal allaqachon `{target.status}` holatida."},
                    status=status.HTTP_409_CONFLICT,
                )
            target.user.template_balance = F("template_balance") - target.amount
            target.user.save(update_fields=["template_balance", "updated_at"])
            target.status = WithdrawalStatusEnum.APPROVED.value
            target.reviewed_by = request.user
            target.reviewed_at = timezone.now()
            target.save()
            log_admin_action(
                actor=request.user,
                action="withdrawal.approve",
                target=target,
                before={"status": WithdrawalStatusEnum.PENDING.value},
                after={"status": target.status, "amount": str(target.amount)},
                note=serializer.validated_data.get("note", "")[:255],
                request=request,
            )
        target.refresh_from_db()
        return Response(self.get_serializer(target).data)

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        serializer = AdminWithdrawalRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            target = (
                TemplateWithdrawalRequestModel.objects
                .select_for_update()
                .get(pk=pk)
            )
            if target.status != WithdrawalStatusEnum.PENDING.value:
                return Response(
                    {"detail": f"Withdrawal allaqachon `{target.status}` holatida."},
                    status=status.HTTP_409_CONFLICT,
                )
            before = {"status": target.status}
            target.status = WithdrawalStatusEnum.REJECTED.value
            target.rejection_reason = serializer.validated_data["rejection_reason"]
            target.reviewed_by = request.user
            target.reviewed_at = timezone.now()
            target.save()
            log_admin_action(
                actor=request.user,
                action="withdrawal.reject",
                target=target,
                before=before,
                after={"status": target.status, "rejection_reason": target.rejection_reason},
                request=request,
            )
        return Response(self.get_serializer(target).data)
