# type: ignore
"""
Plan serializers
"""
from rest_framework import serializers
from core.apps.api.models import PlanModel


class PlanSerializer(serializers.ModelSerializer):
    """Tarif serializer"""

    name_display = serializers.CharField(source="get_name_display", read_only=True)

    class Meta:
        model = PlanModel
        fields = [
            "id",
            "name",
            "name_display",
            "price",
            "max_users",
            "max_bots",
            "max_output_tokens",
            "max_input_tokens",
            "features",
            "powered_by_botmother",
            "custom_domain",
            "is_top",
            "priority_support",
            "description",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "name_display"]
