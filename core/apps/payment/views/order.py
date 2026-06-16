from decimal import Decimal
import logging

from django.db.models import Count, Sum
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
    payer_first_name = data.get("payer_first_name") or ""
    payer_last_name = data.get("payer_last_name") or ""
    payer_username = data.get("payer_username") or ""

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
        payer_first_name=payer_first_name,
        payer_last_name=payer_last_name,
        payer_username=payer_username,
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

    # Paycue (Humo-karta avtomatizatsiyasi) — pay_url YO'Q. Foydalanuvchi
    # moslashtirilgan summani kartaga o'tkazadi; pay_instruction matni qaytadi.
    pay_url = ""
    pay_instruction = ""
    if provider == "paycue":
        from core.apps.payment.services.paycue import PaycueError, create_transaction

        try:
            pc = create_transaction(int(amount))
        except PaycueError as exc:
            logger.error("order_create paycue: %s order_id=%s", exc, order.pk)
            return Response(
                {"status": False, "data": {"provider": f"paycue: {exc}"}},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        # Webhook tranzaksiyani transaction_id bo'yicha topadi.
        order.external_id = pc["transaction_id"]
        order.save(update_fields=["external_id"])
        # Karta tranzaksiya bilan keladi; bo'lmasa PAYCUE_CARD env'ga fallback.
        card_number = pc.get("card_number") or getattr(settings, "PAYCUE_CARD", "")
        pay_instruction = _paycue_instruction(pc["amount"], card_number, pc.get("card_owner", ""))
    else:
        pay_url = _generate_pay_url(txn.pk, amount, provider)

    return Response(
        {
            "status": True,
            "data": {
                "order_id": order.pk,
                "pay_url": pay_url,
                "pay_instruction": pay_instruction,
                "amount": str(order.amount),
                "net_amount": str(order.net_amount),
                "commission": str(order.commission),
            },
        },
        status=status.HTTP_201_CREATED,
    )


def _paycue_instruction(amount: int, card_number: str, card_owner: str = "") -> str:
    """Paycue to'lov ko'rsatmasi matni (HTML). Foydalanuvchi ANIQ shu summani yuboradi."""
    amount_str = f"{amount:,}".replace(",", " ")
    lines = [f"💳 To'lov uchun ANIQ <b>{amount_str} so'm</b> o'tkazing:"]
    if card_number:
        lines.append(f"\n💳 Karta: <code>{card_number}</code>")
        if card_owner:
            lines.append(f"\n👤 {card_owner}")
    lines.append("\n\n⚠️ Summani O'ZGARTIRMANG — aniq shu miqdorni yuboring. To'lov avtomatik tasdiqlanadi.")
    return "".join(lines)


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
    import hmac

    expected = getattr(settings, "INTERNAL_API_TOKEN", None)
    if not expected:
        return False
    provided = request.META.get("HTTP_X_INTERNAL_TOKEN", "")
    return bool(provided and hmac.compare_digest(str(provided), str(expected)))


@extend_schema(tags=["payment-order"])
class EarningsView(BaseViewSetMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    """Egasining daromadlari: balans + bot to'lovlari ro'yxati (paid orderlar).

    ``GET /api/earnings/<id>/`` — bitta order tafsiloti (to'lovchi ma'lumotlari
    bilan), egaga tegishli har qanday holatdagi order.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = EarningsOrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaymentOrderFilter

    def get_queryset(self):
        qs = PaymentOrderModel.objects.filter(owner=self.request.user).select_related("project")
        # Detail uchun istalgan holatdagi order; ro'yxat uchun faqat paid.
        if self.action == "retrieve":
            return qs
        return qs.filter(status=PaymentOrderStatusEnum.PAID).order_by("-paid_at", "-id")

    def list(self, request, *args, **kwargs):
        # Umumiy ko'rsatkichlar (balans, jami, bot bo'yicha taqsimot) har doim
        # to'liq to'plamdan hisoblanadi; faqat orders ro'yxati filtrlanadi
        # (bot bo'yicha filtr orders jadvaliga tegishli).
        base_qs = self.get_queryset()

        agg = base_qs.aggregate(
            total_earned=Coalesce(Sum("net_amount"), Decimal("0")),
            total_commission=Coalesce(Sum("commission"), Decimal("0")),
        )
        request.user.refresh_from_db(fields=["balance"])

        # Bot bo'yicha taqsimot: qaysi botdan qancha daromad tushgani.
        by_bot = (
            base_qs.values("project_id", "project__name")
            .annotate(
                total_earned=Coalesce(Sum("net_amount"), Decimal("0")),
                count=Count("id"),
            )
            .order_by("-total_earned")
        )

        # Yechiladigan bot daromadi: jami sof daromad − band qilingan yechishlar
        # (o'zi to'ldirgan pul hisobga olinmaydi).
        from core.apps.payment.services.withdrawal import get_reserved

        reserved = get_reserved(request.user)
        withdrawable = agg["total_earned"] - reserved
        if withdrawable < 0:
            withdrawable = Decimal("0")

        # Tekis payload: balans/jami + bot taqsimoti + pagination meta + orders.
        # BaseViewSetMixin.finalize_response uni {status, data: payload} ga o'raydi.
        payload = {
            "balance": request.user.balance,
            "withdrawable": str(withdrawable),
            "total_earned": str(agg["total_earned"]),
            "total_commission": str(agg["total_commission"]),
            "by_bot": [
                {
                    "project_id": row["project_id"],
                    "project_name": row["project__name"],
                    "total_earned": str(row["total_earned"]),
                    "count": row["count"],
                }
                for row in by_bot
            ],
        }

        qs = self.filter_queryset(base_qs)
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
