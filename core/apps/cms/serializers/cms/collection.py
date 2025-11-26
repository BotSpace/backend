# type: ignore
import logging
from django.db.transaction import atomic
from bson import ObjectId
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.apps.cms.enums.cms import FieldType
from core.apps.cms.models import CollectionModel
from core.apps.cms.models.cms import FieldModel
from core.apps.cms.serializers.cms.field import CreateFieldSerializer, RetrieveFieldSerializer
from core.apps.api.models import ProjectModel
from datetime import datetime, timezone
from dateutil import parser
import re


def to_datetime_safe(value: str) -> datetime:
    """
    Har qanday vaqt stringini xavfsiz datetime ga aylantiradi.
    Nanosecond -> microsecond ga avtomatik moslashtiradi.
    """

    if not isinstance(value, str):
        raise ValueError("Datetime must be string")

    # 1) Nanosecond (9 digit) aniqlash va 6 digitgacha qisqartirish
    match = re.search(r"\.(\d+)", value)
    if match:
        fraction = match.group(1)
        if len(fraction) > 6:  # nano → micro
            value = value.replace("." + fraction, "." + fraction[:6])  # faqat 6 ta raqam qoldiramiz

    # 2) dateutil orqali parse
    dt = parser.parse(value)

    # 3) Agar timezone bo'lmasa — UTC qilamiz
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


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
    project = serializers.PrimaryKeyRelatedField(
        queryset=ProjectModel.objects.all(),
        required=True,
        allow_null=False,
    )

    class Meta(BaseCollectionSerializer.Meta):
        fields = [
            "id",
            "name",
            "project",
            "fields",
        ]
        extra_kwargs = {"project": {"required": True}}

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
            raise ValidationError(detail={"where": ["where is not dict"]})
        for field, _value in value.items():
            if field == "_id":
                if isinstance(_value, dict) and "$oid" in _value:
                    value[field] = ObjectId(_value["$oid"])
                    break
                value[field] = ObjectId(_value)
                break
        return value


class AddDataCollectionSerializer(BaseDataCollectionSerializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise ValidationError(detail="Expected a JSON object")
        validated = {}
        for field, value in data.items():
            try:
                instance = FieldModel.objects.get(collection=self.context.get("collection"), name=field)
            except FieldModel.DoesNotExist:
                logging.info("invalid field")
                continue
            if instance.type == FieldType.DATETIME.value:
                validated[field] = to_datetime_safe(value)
                continue
            validated[field] = value
        return validated


class InsertIfNotExists(BaseDataCollectionSerializer):
    where = serializers.DictField(required=True)
    data = AddDataCollectionSerializer()


class FindDataCollectionSerializer(BaseDataCollectionSerializer):
    limit = serializers.IntegerField(required=False)
    skip = serializers.IntegerField(required=False)
    sort = serializers.DictField(required=False)
    where = serializers.DictField(required=False)


class FindOneDataCollectionSerializer(BaseDataCollectionSerializer):
    where = serializers.DictField(required=True)

    def validate(self, attrs):
        if len(attrs.get("where", {})) <= 0:
            raise ValidationError(detail={"where": ["where is empty"]})
        return attrs


class CountDataCollectionSerializer(BaseDataCollectionSerializer):
    """Serializer for counting documents in collection"""

    where = serializers.DictField(required=False)


class DeleteDataCollectionSerializer(BaseDataCollectionSerializer):
    where = serializers.DictField(required=True)


class UpdateDataCollectionSerializer(BaseDataCollectionSerializer):
    where = serializers.DictField(required=False)
    data = serializers.DictField(required=True)
