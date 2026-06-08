from decimal import Decimal
import logging

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.conf import settings

from django_core.mixins import BaseViewSetMixin
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, mixins
from rest_framework_simplejwt.authentication import JWTAuthentication

from click_up import ClickUp
from config.env import env

from core.apps.api.models.project import ProjectModel
from core.apps.payment.enums.payment import PaymentOrderStatusEnum
from core.apps.payment.filters.order import PaymentOrderFilter  # type: ignore[import]
from core.apps.payment.models.order import PaymentOrderModel
from core.apps.payment.models.transaction import TransactionModel
from core.apps.payment.serializers.order import (
    CreateOrderSerializer,
    EarningsOrderSerializer,
    EarningsSerializer,
    OrderStatusSerializer,
)
from core.apps.payment.services.commission import calculate_commission
from core.apps.shared.permissions.internal_token import IsInternalTokenOnly

logger = logging.getLogger(__name__)


@extend_schema(tags=["payment-order"])
@api_view(["POST"])
@authentication_classes([])
@permission_classes([IsInternalTokenOnly])
@throttle_classes([])
def order_create(request):
    """Engine → backend: bot foydalanuvchisi uchun Click to'lov orderi yaratadi.

    Faqat X-Internal-Token bilan ishlaydi.
    """
    serializer = CreateOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"status": False, "data": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Project topish (soft-delete'ni ham ko'rish uchun _base_manager yo'q;
    # SoftDeleteManager faqat alive row'larni qaytaradi — bu to'g'ri xatti-harakat)
    try:
        project = ProjectModel.objects.get(pk=data["project_id"])
    except ProjectModel.DoesNotExist:
        return Response(
            {"status": False, "data": {"project_id": "Loyiha topilmadi"}},
            status=status.HTTP_404_NOT_FOUND,
        )

    owner = project.owner
    amount = data["amount"]
    provider = data.get("provider", "click")
    comment = data.get("comment") or ""
    idempotency_key = data.get("idempotency_key") or None
    is_debug = data.get("is_debug", False)

    # Idempotency: agar bunday key bilan order mavjud bo'lsa uni qaytaramiz
    if idempotency_key:
        existing = PaymentOrderModel.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            # Mavjud order uchun txn bo'lmasa (eski order) — txn yaratib bog'laymiz
            if existing.transaction_id is None:
                txn = TransactionModel.objects.create(user=owner, amount=existing.amount)
                existing.transaction = txn
                existing.save(update_fields=["transaction"])
            pay_url = _generate_pay_url(existing.transaction_id, existing.amount, provider)
            return Response(
                {
                    "status": True,
                    "data": {
                        "order_id": existing.pk,
                        "pay_url": pay_url,
                        "amount": str(existing.amount),
                        "net_amount": str(existing.net_amount),
                        "commission": str(existing.commission),
                    },
                }
            )

    # Komissiya audit uchun order yaratilayotganda hisoblanadi
    commission, net_amount = calculate_commission(amount)

    # Har order uchun TransactionModel yaratamiz — Click Prepare shu id'ni qidiradi
    txn = TransactionModel.objects.create(user=owner, amount=amount)

    order = PaymentOrderModel.objects.create(
        project=project,
        owner=owner,
        payer_chat_id=data["payer_chat_id"],
        amount=amount,
        commission=commission,
        net_amount=net_amount,
        provider=provider,
        comment=comment,
        status=PaymentOrderStatusEnum.CREATED,
        idempotency_key=idempotency_key,
        transaction=txn,
        is_debug=is_debug,
    )

    pay_url = _generate_pay_url(txn.pk, amount, provider)

    return Response(
        {
            "status": True,
            "data": {
                "order_id": order.pk,
                "pay_url": pay_url,
                "amount": str(order.amount),
                "net_amount": str(order.net_amount),
                "commission": str(order.commission),
            },
        },
        status=status.HTTP_201_CREATED,
    )


def _generate_pay_url(txn_pk: int, amount, provider: str) -> str:
    """Click pay_url generatsiya qiladi. merchant_trans_id = txn.pk (raqamli, prefikssiz)."""
    if provider == "click":
        click_up = ClickUp(
            service_id=env.str("CLICK_SERVICE_ID"),
            merchant_id=env.str("CLICK_MERCHANT_ID"),
        )
        return_url = getattr(settings, "PAYMENT_RETURN_URL", "https://botspace.uz")
        return click_up.initializer.generate_pay_link(
            id=txn_pk,
            amount=amount,
            return_url=return_url,
        )
    # TODO: Payme/Uzum (Faza 5)
    return ""


@extend_schema(tags=["payment-order"])
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([])
@throttle_classes([])
def order_status(request, order_id: int):
    """Order holati. Engine reconnect'da (internal token) yoki egasi (JWT) ko'ra oladi."""
    is_internal = _check_internal_token(request)
    is_authed = hasattr(request, "user") and request.user and request.user.is_authenticated

    if not is_internal and not is_authed:
        return Response({"status": False, "data": {"detail": "Autentifikatsiya kerak"}}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        order = PaymentOrderModel.objects.get(pk=order_id)
    except PaymentOrderModel.DoesNotExist:
        return Response({"status": False, "data": {"detail": "Topilmadi"}}, status=status.HTTP_404_NOT_FOUND)

    # JWT auth bo'lsa faqat o'zining orderini ko'radi
    if not is_internal and is_authed and order.owner_id != request.user.pk:
        return Response({"status": False, "data": {"detail": "Ruxsat yo'q"}}, status=status.HTTP_403_FORBIDDEN)

    serializer = OrderStatusSerializer(order)
    return Response({"status": True, "data": serializer.data})


def _check_internal_token(request) -> bool:
    expected = getattr(settings, "INTERNAL_API_TOKEN", None)
    if not expected:
        return False
    provided = request.META.get("HTTP_X_INTERNAL_TOKEN", "")
    return bool(provided and provided == expected)


@extend_schema(tags=["payment-order"])
class EarningsView(BaseViewSetMixin, mixins.ListModelMixin, GenericViewSet):
    """Egasining daromadlari: balans + bot to'lovlari ro'yxati (paid orderlar)."""

    permission_classes = [IsAuthenticated]
    serializer_class = EarningsOrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaymentOrderFilter

    def get_queryset(self):
        return (
            PaymentOrderModel.objects.filter(
                owner=self.request.user,
                status=PaymentOrderStatusEnum.PAID,
            )
            .select_related("project")
            .order_by("-paid_at", "-id")
        )

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        agg = qs.aggregate(
            total_earned=Coalesce(Sum("net_amount"), Decimal("0")),
            total_commission=Coalesce(Sum("commission"), Decimal("0")),
        )
        request.user.refresh_from_db(fields=["balance"])

        # Tekis payload: balans/jami + pagination meta + orders bir darajada.
        # BaseViewSetMixin.finalize_response uni {status, data: payload} ga o'raydi.
        payload = {
            "balance": request.user.balance,
            "total_earned": str(agg["total_earned"]),
            "total_commission": str(agg["total_commission"]),
        }

        page = self.paginate_queryset(qs)
        if page is not None:
            orders_data = EarningsOrderSerializer(page, many=True).data
            meta = self.get_paginated_response(orders_data).data
            payload.update(
                {
                    "count": meta.get("count"),
                    "next": meta.get("next"),
                    "previous": meta.get("previous"),
                    "orders": list(meta.get("results", orders_data)),
                }
            )
        else:
            payload["orders"] = list(EarningsOrderSerializer(qs, many=True).data)

        return Response(payload)
