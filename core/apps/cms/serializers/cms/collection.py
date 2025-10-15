# type: ignore
from bson import ObjectId
from django.http import request
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

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
    class Meta(BaseCollectionSerializer.Meta):
        fields = [*BaseCollectionSerializer.Meta.fields, "fields"]


class CreateCollectionSerializer(BaseCollectionSerializer):
    class Meta(BaseCollectionSerializer.Meta):
        fields = [
            "id",
            "name",
        ]


class BaseDataCollectionSerializer(serializers.Serializer):
    def validate_where(self, value):
        if not isinstance(value, dict):
            raise ValidationError(detail={"where": "where is not dict"})
        for field, _value in value.items():
            if field == "_id":
                value[field] = ObjectId(_value)
                break
        return value


class AddDataCollectionSerializer(BaseDataCollectionSerializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise ValidationError(detail="Expected a JSON object")
        validated = {}
        for field, value in data.items():
            validated[field] = value
        return validated


class FindDataCollectionSerializer(BaseDataCollectionSerializer):
    limit = serializers.IntegerField(required=False)
    sort = serializers.DictField(required=False)
    where = serializers.DictField(required=False)


class FindOneDataCollectionSerializer(BaseDataCollectionSerializer):
    where = serializers.DictField(required=True)


class DeleteDataCollectionSerializer(BaseDataCollectionSerializer):
    where = serializers.DictField(required=True)


class UpdateDataCollectionSerializer(BaseDataCollectionSerializer):
    where = serializers.DictField(required=False)
    data = serializers.DictField(required=True)
