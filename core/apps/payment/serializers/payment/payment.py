from rest_framework import serializers

from core.apps.payment.enums.payment import PaymentMethosEnum


class CreatePaymentLinkSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=PaymentMethosEnum.choices)
    amount = serializers.IntegerField()
