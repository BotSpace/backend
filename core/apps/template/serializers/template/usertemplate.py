from rest_framework import serializers

from core.apps.template.models import UserTemplateModel


class BaseUsertemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTemplateModel
        fields = [
            "id",
        ]


class ListUsertemplateSerializer(BaseUsertemplateSerializer):
    class Meta(BaseUsertemplateSerializer.Meta): ...


class RetrieveUsertemplateSerializer(BaseUsertemplateSerializer):
    class Meta(BaseUsertemplateSerializer.Meta): ...


class CreateUsertemplateSerializer(BaseUsertemplateSerializer):
    class Meta(BaseUsertemplateSerializer.Meta):
        fields = [
            "id",
        ]
