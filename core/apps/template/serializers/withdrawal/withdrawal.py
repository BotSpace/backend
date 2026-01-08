from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from core.apps.template.models.withdrawal import TemplateWithdrawalRequestModel


class BaseTemplateWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateWithdrawalRequestModel
        fields = [
            "id",
            "amount",
            "card_number",
            "card_owner",
            "status",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class ListTemplateWithdrawalSerializer(BaseTemplateWithdrawalSerializer):
    class Meta(BaseTemplateWithdrawalSerializer.Meta):
        pass


class RetrieveTemplateWithdrawalSerializer(BaseTemplateWithdrawalSerializer):
    class Meta(BaseTemplateWithdrawalSerializer.Meta):
        pass


class CreateTemplateWithdrawalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateWithdrawalRequestModel
        fields = [
            "amount",
            "card_number",
            "card_owner",
        ]
    
    def validate_amount(self, value):
        """Validate that user has sufficient template balance"""
        user = self.context['request'].user
        if value <= 0:
            raise serializers.ValidationError(_("Amount must be greater than 0"))
        if value > user.template_balance:
            raise serializers.ValidationError(
                _("Insufficient template balance. Available: %(balance)s") % {'balance': user.template_balance}
            )
        return value
    
    def validate_card_number(self, value):
        """Basic validation for card number"""
        # Remove spaces and check if it's numeric
        card_num = value.replace(" ", "")
        if not card_num.isdigit():
            raise serializers.ValidationError(_("Card number must contain only digits"))
        if len(card_num) < 13 or len(card_num) > 19:
            raise serializers.ValidationError(_("Card number must be between 13 and 19 digits"))
        return value
