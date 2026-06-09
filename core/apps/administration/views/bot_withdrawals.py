# type: ignore
"""Admin Bot Withdrawals — bot daromadlaridan pul yechishni tasdiqlash/rad etish.

Tasdiqlashda umumiy balansdan (``User.balance``) summa atomik ayriladi.
"""

from django.db import transaction
from django.utils import timezone
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.bot_withdrawals import (
    AdminBotWithdrawalApproveSerializer,
    AdminBotWithdrawalRejectSerializer,
    AdminBotWithdrawalSerializer,
)
from core.apps.administration.services import log_admin_action
from core.apps.payment.enums.withdrawal import WithdrawalStatusEnum
from core.apps.payment.models.withdrawal import WithdrawalRequestModel
from core.apps.payment.services.balance import subtract_balance


class AdminBotWithdrawalsView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminBotWithdrawalSerializer

    def get_queryset(self):
        qs = (
            WithdrawalRequestModel.objects
            .select_related("user", "project", "reviewed_by")
            .order_by("-id")
        )
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        serializer = AdminBotWithdrawalApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            target = (
                WithdrawalRequestModel.objects
                .select_for_update()
                .select_related("user")
                .get(pk=pk)
            )
            if target.status != WithdrawalStatusEnum.PENDING.value:
                return Response(
                    {"detail": f"So'rov allaqachon `{target.status}` holatida."},
                    status=status.HTTP_409_CONFLICT,
                )
            user = target.user
            user.refresh_from_db(fields=["balance"])
            if user.balance < target.amount:
                return Response(
                    {"detail": "Foydalanuvchi balansi yetarli emas."},
                    status=status.HTTP_409_CONFLICT,
                )
            # Balansdan ayirish + history yozuvi (idempotent).
            subtract_balance(
                user,
                target.amount,
                comment=f"Pul yechish #{target.pk}",
                idempotency_key=f"withdrawal:{target.pk}",
            )
            target.status = WithdrawalStatusEnum.APPROVED.value
            target.reviewed_by = request.user
            target.reviewed_at = timezone.now()
            target.save()
            log_admin_action(
                actor=request.user,
                action="bot_withdrawal.approve",
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
        serializer = AdminBotWithdrawalRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            target = (
                WithdrawalRequestModel.objects
                .select_for_update()
                .get(pk=pk)
            )
            if target.status != WithdrawalStatusEnum.PENDING.value:
                return Response(
                    {"detail": f"So'rov allaqachon `{target.status}` holatida."},
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
                action="bot_withdrawal.reject",
                target=target,
                before=before,
                after={"status": target.status, "rejection_reason": target.rejection_reason},
                request=request,
            )
        return Response(self.get_serializer(target).data)
