from rest_framework import serializers

from core.apps.api.models import BotModel


class BaseBotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotModel
        fields = [
            "id",
            "name",
        ]


class ListBotSerializer(BaseBotSerializer):
    class Meta(BaseBotSerializer.Meta): ...


class RetrieveBotSerializer(BaseBotSerializer):
    class Meta(BaseBotSerializer.Meta): ...


class CreateBotSerializer(BaseBotSerializer):
    class Meta(BaseBotSerializer.Meta):
        fields = [
            "id",
            "name",
        ]
