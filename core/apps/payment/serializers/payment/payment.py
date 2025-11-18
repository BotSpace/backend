from rest_framework import serializers

from core.apps.payment.enums.payment import PaymentMethosEnum
from core.apps.template.models.order import TemplateOrderModel


class CreatePaymentLinkSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=PaymentMethosEnum.choices)
    order = serializers.PrimaryKeyRelatedField(queryset=TemplateOrderModel.objects.all())
