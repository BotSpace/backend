from rest_framework import serializers

from core.apps.cms.models import CollectionModel


class BaseCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionModel
        fields = [
            "id",
            "name",
        ]


class ListCollectionSerializer(BaseCollectionSerializer):
    class Meta(BaseCollectionSerializer.Meta): ...


class RetrieveCollectionSerializer(BaseCollectionSerializer):
    class Meta(BaseCollectionSerializer.Meta): ...


class CreateCollectionSerializer(BaseCollectionSerializer):
    class Meta(BaseCollectionSerializer.Meta):
        fields = [
            "id",
            "name",
        ]
