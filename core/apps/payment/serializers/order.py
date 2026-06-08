from decimal import Decimal

from rest_framework import serializers

from core.apps.payment.enums.payment import PaymentMethosEnum, PaymentOrderStatusEnum
from core.apps.payment.models.order import PaymentOrderModel


class CreateOrderSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    payer_chat_id = serializers.IntegerField()
    amount = serializers.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=Decimal("1000"),
        error_messages={"min_value": "Minimal to'lov summasi 1000 so'm."},
    )
    comment = serializers.CharField(max_length=512, required=False, allow_blank=True, default="")
    provider = serializers.ChoiceField(
        choices=PaymentMethosEnum.choices,
        required=False,
        default=PaymentMethosEnum.CLICK,
    )
    idempotency_key = serializers.CharField(max_length=128, required=False, allow_blank=True, default=None)
    is_debug = serializers.BooleanField(required=False, default=False)


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentOrderModel
        fields = ["id", "status", "amount", "net_amount", "commission", "paid_at", "provider", "comment"]
        read_only_fields = fields


class EarningsOrderSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = PaymentOrderModel
        fields = [
            "id",
            "project_id",
            "project_name",
            "payer_chat_id",
            "amount",
            "commission",
            "net_amount",
            "status",
            "provider",
            "comment",
            "created_at",
            "paid_at",
        ]
        read_only_fields = fields


class EarningsSerializer(serializers.Serializer):
    balance = serializers.IntegerField()
    total_earned = serializers.DecimalField(max_digits=20, decimal_places=2)
    total_commission = serializers.DecimalField(max_digits=20, decimal_places=2)
    orders = EarningsOrderSerializer(many=True)
