# type: ignore
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "phone",
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "balance",
            "template_balance",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "validated_at",
        )
        read_only_fields = fields


class AdminUserBalanceSerializer(serializers.Serializer):
    field = serializers.ChoiceField(choices=("balance", "template_balance"))
    value = serializers.DecimalField(max_digits=20, decimal_places=2)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdminUserBanSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
