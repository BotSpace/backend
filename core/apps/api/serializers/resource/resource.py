from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.apps.api.models import ResourceModel


class BaseResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceModel
        fields = [
            "id",
            "user",
            "project",
            "hostname",
            "ram",
            "cpu",
            "net_rx",
            "net_tx",
        ]


class ListResourceSerializer(BaseResourceSerializer):
    class Meta(BaseResourceSerializer.Meta): ...


class RetrieveResourceSerializer(BaseResourceSerializer):
    class Meta(BaseResourceSerializer.Meta): ...


class CreateResourceSerializer(BaseResourceSerializer):

    def validate_project(self, value):
        request = self.context.get("request")
        if request is None:
            raise Exception("request is None")
        if value.owner.pk != request.user.pk:
            raise ValidationError(detail={"project": "Siz project egasi emassiz!!!"})
        return value

    class Meta(BaseResourceSerializer.Meta):
        fields = [
            "id",
            "user",
            "project",
            "hostname",
            "ram",
            "cpu",
            "net_rx",
            "net_tx",
        ]
        extra_kwargs = {
            "user": {"read_only": True},
        }
