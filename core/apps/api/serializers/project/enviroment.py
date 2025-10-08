from rest_framework import serializers

from core.apps.api.models import EnviromentModel


class BaseEnviromentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnviromentModel
        fields = [
            "id",
            "key",
            "value",
        ]


class ListEnviromentSerializer(BaseEnviromentSerializer):
    class Meta(BaseEnviromentSerializer.Meta): ...


class RetrieveEnviromentSerializer(BaseEnviromentSerializer):
    class Meta(BaseEnviromentSerializer.Meta): ...


class CreateEnviromentSerializer(BaseEnviromentSerializer):
    class Meta(BaseEnviromentSerializer.Meta):
        fields = [
            "id",
            "key",
            "value",
            "project",
        ]
