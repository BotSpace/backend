from rest_framework import serializers

from core.apps.cms.models import FieldModel


class BaseFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldModel
        fields = [
            "id",
            "name",
        ]


class ListFieldSerializer(BaseFieldSerializer):
    class Meta(BaseFieldSerializer.Meta): ...


class RetrieveFieldSerializer(BaseFieldSerializer):
    class Meta(BaseFieldSerializer.Meta): ...


class CreateFieldSerializer(BaseFieldSerializer):
    class Meta(BaseFieldSerializer.Meta):
        fields = [
            "id",
            "name",
        ]
