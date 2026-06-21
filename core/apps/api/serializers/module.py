from rest_framework import serializers

from core.apps.api.models.module import ModuleModel, ProjectModuleModel


class ModuleSerializer(serializers.ModelSerializer):
    docs = serializers.SerializerMethodField()
    nodes_summary = serializers.SerializerMethodField()

    def get_docs(self, instance):
        cache = instance.manifest_cache or {}
        return cache.get("docs", "")

    def get_nodes_summary(self, instance):
        cache = instance.manifest_cache or {}
        nodes = cache.get("nodes", [])
        return [
            {
                "type": n.get("type"),
                "title": n.get("title") or n.get("name") or n.get("type", ""),
                "category": n.get("category", ""),
                "trigger": bool(n.get("trigger") or n.get("category") == "triggers"),
            }
            for n in nodes
        ]

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
            "docs",
            "nodes_summary",
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
