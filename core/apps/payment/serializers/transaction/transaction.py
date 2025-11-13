from rest_framework import serializers

from core.apps.payment.models import TransactionModel


class BaseTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionModel
        fields = [
            "id",
            "name",
        ]


class ListTransactionSerializer(BaseTransactionSerializer):
    class Meta(BaseTransactionSerializer.Meta): ...


class RetrieveTransactionSerializer(BaseTransactionSerializer):
    class Meta(BaseTransactionSerializer.Meta): ...


class CreateTransactionSerializer(BaseTransactionSerializer):
    class Meta(BaseTransactionSerializer.Meta):
        fields = [
            "id",
            "name",
        ]
