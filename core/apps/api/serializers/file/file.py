import os
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from core.apps.api.models import FileModel
from core.apps.api.serializers.fields import ProjectPkOrUuidField


class BaseFileSerializer(serializers.ModelSerializer):
    # Frontend uchun qo'shimcha read fieldlar
    id = serializers.IntegerField(source="pk", read_only=True)
    name = serializers.SerializerMethodField(read_only=True)
    url = serializers.SerializerMethodField(read_only=True)
    size = serializers.IntegerField(source="filesize", read_only=True)
    mime = serializers.CharField(source="filetype", read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = FileModel
        fields = [
            # eski fieldlar (boshqa consumer'lar uchun saqlanadi)
            "file",
            "uuid",
            "filesize",
            "filetype",
            "project",
            # yangi read fieldlar (frontend uchun)
            "id",
            "name",
            "url",
            "size",
            "mime",
            "created_at",
            "expires_at",
        ]

    def get_name(self, obj):
        if obj.file and obj.file.name:
            return os.path.basename(obj.file.name)
        return None

    def get_url(self, obj):
        if not obj.file:
            return None
        try:
            raw_url = obj.file.url
        except Exception:
            return None
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(raw_url)
        return raw_url


class ListFileSerializer(BaseFileSerializer):
    class Meta(BaseFileSerializer.Meta): ...


class RetrieveFileSerializer(BaseFileSerializer):
    class Meta(BaseFileSerializer.Meta): ...


class CreateFileSerializer(BaseFileSerializer):
    project = ProjectPkOrUuidField()
    ttl = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Saqlash muddati soniyalarda. null yoki 0 = doimiy.",
    )

    class Meta(BaseFileSerializer.Meta):
        fields = [
            "file",
            "uuid",
            "filesize",
            "filetype",
            "project",
            # yangi read fieldlar
            "id",
            "name",
            "url",
            "size",
            "mime",
            "created_at",
            "expires_at",
            # write-only
            "ttl",
        ]
        extra_kwargs = {
            "uuid": {"read_only": True},
            "filesize": {"read_only": True},
        }

    def create(self, validated_data):
        ttl = validated_data.pop("ttl", None)
        instance = super().create(validated_data)
        if ttl and ttl > 0:
            instance.expires_at = timezone.now() + timedelta(seconds=ttl)
            instance.save(update_fields=["expires_at"])
        return instance


class ModuleFileCreateSerializer(BaseFileSerializer):
    """project va user token orqali beriladi — input sifatida qabul qilinmaydi."""

    ttl = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text="Saqlash muddati soniyalarda. null yoki 0 = doimiy.",
    )

    class Meta(BaseFileSerializer.Meta):
        fields = [
            "file",
            "uuid",
            "filesize",
            "filetype",
            # yangi read fieldlar
            "id",
            "name",
            "url",
            "size",
            "mime",
            "created_at",
            "expires_at",
            # write-only
            "ttl",
        ]
        extra_kwargs = {
            "uuid": {"read_only": True},
            "filesize": {"read_only": True},
        }

    def create(self, validated_data):
        ttl = validated_data.pop("ttl", None)
        instance = super().create(validated_data)
        if ttl and ttl > 0:
            instance.expires_at = timezone.now() + timedelta(seconds=ttl)
            instance.save(update_fields=["expires_at"])
        return instance
