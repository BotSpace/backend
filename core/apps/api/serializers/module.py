from rest_framework import serializers

from core.apps.api.models.module import ModuleModel, ProjectModuleModel


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleModel
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "icon",
            "github_url",
            "image",
            "port",
            "active",
            "manifest_cache",
            "manifest_fetched_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "manifest_cache", "manifest_fetched_at", "created_at", "updated_at"]


class CreateModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleModel
        fields = ["slug", "name", "description", "icon", "github_url", "image", "port", "auth_token", "active"]


class ProjectModuleSerializer(serializers.ModelSerializer):
    module = ModuleSerializer(read_only=True)
    module_slug = serializers.CharField(write_only=True)

    class Meta:
        model = ProjectModuleModel
        fields = [
            "id",
            "module",
            "module_slug",
            "enabled",
            "config",
            "service_id",
            "endpoint",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "service_id", "endpoint", "status", "created_at", "updated_at"]


class EnableModuleSerializer(serializers.Serializer):
    module_slug = serializers.SlugField()
