# type: ignore
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    tokens_used_input = serializers.SerializerMethodField()
    tokens_used_output = serializers.SerializerMethodField()
    # Populated via queryset annotation (see AdminUsersView.get_queryset) — sortable.
    tokens_used_total = serializers.IntegerField(read_only=True)

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
            "tokens_used_input",
            "tokens_used_output",
            "tokens_used_total",
        )
        read_only_fields = fields

    def get_tokens_used_input(self, obj) -> int:
        sub = getattr(obj, "subscription", None)
        return sub.tokens_used_input if sub is not None else 0

    def get_tokens_used_output(self, obj) -> int:
        sub = getattr(obj, "subscription", None)
        return sub.tokens_used_output if sub is not None else 0


class AdminUserBalanceSerializer(serializers.Serializer):
    field = serializers.ChoiceField(choices=("balance", "template_balance"))
    value = serializers.DecimalField(max_digits=20, decimal_places=2)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AdminUserBanSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
