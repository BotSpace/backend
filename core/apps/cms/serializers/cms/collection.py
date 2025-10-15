# type: ignore
from django.db.transaction import atomic
from bson import ObjectId
from django.http import request
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.apps.cms.enums.cms import FieldType
from core.apps.cms.models import CollectionModel
from core.apps.cms.models.cms import FieldModel
from core.apps.cms.serializers.cms.field import CreateFieldSerializer, RetrieveFieldSerializer
from core.apps.cms.services.collection import collection_validate_data


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
    fields = RetrieveFieldSerializer(many=True)

    class Meta(BaseCollectionSerializer.Meta):
        fields = [*BaseCollectionSerializer.Meta.fields, "fields"]


class CreateCollectionSerializer(BaseCollectionSerializer):
    fields = CreateFieldSerializer(many=True, required=False)

    class Meta(BaseCollectionSerializer.Meta):
        fields = [
            "id",
            "name",
            "fields",
        ]

    def create(self, validated_data):
        if "fields" in validated_data:
            fields = validated_data.pop("fields")
            with atomic():
                collection = CollectionModel.objects.create(**validated_data)
                fields_obj = [FieldModel(collection=collection, **fd) for fd in fields]
                FieldModel.objects.bulk_create(fields_obj)
                return collection
        return CollectionModel.objects.create(**validated_data)


class UpdateCollectionSerializer(BaseCollectionSerializer):
    fields = CreateFieldSerializer(many=True, required=False)

    class Meta(BaseCollectionSerializer.Meta):
        fields = [
            "fields",
        ]

    def update(self, instance, validated_data):
        if "fields" in validated_data:
            fields = validated_data.pop("fields")
            with atomic():
                for field in fields:
                    defaults = {}
                    if "required" in field:
                        defaults["required"] = field.get("required", False)
                    if "type" in field:
                        defaults["type"] = field.get("type", FieldType.TEXT.value)
                    if "default" in field:
                        defaults["default"] = field.get("default", None)
                    FieldModel.objects.update_or_create(collection=instance, name=field["name"], defaults=defaults)
                FieldModel.objects.filter(collection=instance).exclude(name__in=[f["name"] for f in fields]).delete()
        return super().update(instance, validated_data)


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
