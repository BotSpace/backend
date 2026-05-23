from __future__ import annotations

from rest_framework import serializers

from core.apps.cms.enums import FieldKind, IndexKind
from core.apps.cms.models import Collection, Field


class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Field
        fields = [
            "id",
            "name",
            "label",
            "kind",
            "required",
            "default",
            "validators",
            "relation_collection",
            "cascade",
            "index",
            "order",
        ]
        read_only_fields = ["id"]


class CollectionListSerializer(serializers.ModelSerializer):
    fields_count = serializers.SerializerMethodField()
    can_delete = serializers.BooleanField(read_only=True)

    class Meta:
        model = Collection
        fields = [
            "id",
            "project",
            "name",
            "label",
            "description",
            "system",
            "schema_version",
            "fields_count",
            "can_delete",
            "created_at",
            "updated_at",
        ]

    def get_fields_count(self, obj: Collection) -> int:
        # `.fields` clashes with DRF — use the related manager directly.
        return obj.fields.count()


class CollectionDetailSerializer(CollectionListSerializer):
    fields = FieldSerializer(many=True, read_only=True)

    class Meta(CollectionListSerializer.Meta):
        fields = CollectionListSerializer.Meta.fields + ["fields"]


class CollectionCreateSerializer(serializers.ModelSerializer):
    fields = FieldSerializer(many=True, required=False)

    class Meta:
        model = Collection
        fields = ["name", "label", "description", "fields"]

    def validate_name(self, value: str) -> str:
        if not value or not value.replace("_", "").isalnum():
            raise serializers.ValidationError("name must be lowercase alphanumeric (snake_case)")
        return value.lower()

    def create(self, validated_data: dict) -> Collection:
        fields_data = validated_data.pop("fields", []) or []
        project = self.context["project"]
        owner = self.context["request"].user if self.context.get("request") else None
        coll = Collection.objects.create(
            project=project,
            owner=owner if (owner and owner.is_authenticated) else None,
            **validated_data,
        )
        for idx, f in enumerate(fields_data):
            Field.objects.create(collection=coll, order=f.get("order", idx), **f)
        return coll
