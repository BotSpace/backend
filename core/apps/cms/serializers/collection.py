from __future__ import annotations

from django.db import transaction
from rest_framework import serializers

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
            "primary_field",
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
        # `id` is read-only in the response so the client can use it as
        # relation_collection when linking from another collection.
        fields = ["id", "name", "label", "description", "primary_field", "fields"]
        read_only_fields = ["id"]

    def validate_name(self, value: str) -> str:
        if not value or not value.replace("_", "").isalnum():
            raise serializers.ValidationError("name must be lowercase alphanumeric (snake_case)")
        return value.lower()

    def validate_fields(self, value: list[dict]) -> list[dict]:
        names = [str(item.get("name", "")).lower() for item in value]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise serializers.ValidationError(f"duplicate field name(s): {', '.join(duplicates)}")
        return value

    def create(self, validated_data: dict) -> Collection:
        fields_data = validated_data.pop("fields", []) or []
        project = self.context["project"]
        owner = self.context["request"].user if self.context.get("request") else None
        owner = owner if (owner and owner.is_authenticated) else None

        with transaction.atomic():
            coll = Collection.objects.filter(
                project=project,
                name=validated_data["name"],
                deleted_at__isnull=True,
            ).first()
            if coll is None:
                coll = Collection.objects.create(project=project, owner=owner, **validated_data)
            else:
                changed_fields = []
                for attr in ("label", "description", "primary_field"):
                    if attr in validated_data and getattr(coll, attr) != validated_data[attr]:
                        setattr(coll, attr, validated_data[attr])
                        changed_fields.append(attr)
                if owner is not None and coll.owner_id != owner.id:
                    coll.owner = owner
                    changed_fields.append("owner")
                if changed_fields:
                    coll.save(update_fields=[*changed_fields, "updated_at"])

            for idx, field_data in enumerate(fields_data):
                data = dict(field_data)
                field_name = str(data.pop("name")).lower()
                data["order"] = data.get("order", idx)
                Field.objects.update_or_create(
                    collection=coll,
                    name=field_name,
                    defaults=data,
                )

        return coll
