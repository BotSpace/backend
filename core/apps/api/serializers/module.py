from rest_framework import serializers

from core.apps.api.models.module import ModuleModel, ProjectModuleModel


class ModuleSerializer(serializers.ModelSerializer):
    docs = serializers.SerializerMethodField()
    nodes = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    module_yaml = serializers.SerializerMethodField()

    def get_docs(self, instance):
        cache = instance.manifest_cache or {}
        return cache.get("docs", "")

    def get_source(self, instance):
        """Source config (mode/endpoint) parsed from module.yaml."""
        cache = instance.manifest_cache or {}
        src = cache.get("_source") or {}
        if not src.get("mode"):
            src = {"mode": "github" if instance.image else "endpoint", "endpoint": "", "github": instance.github_url or ""}
        return src

    def get_module_yaml(self, instance):
        """Reconstruct module.yaml from stored fields so the admin edit form can
        prefill it (the raw yaml isn't stored — only parsed fields + _source)."""
        src = self.get_source(instance)
        mode = src.get("mode")
        lines = [
            "apiVersion: botmother.module/v1",
            "module:",
            f"  id: {instance.slug}",
            f"  name: {instance.name}",
        ]
        if instance.icon:
            lines.append(f"  icon: {instance.icon}")
        if instance.description:
            lines.append(f"  description: {instance.description}")
        lines.append("source:")
        if mode == "endpoint":
            lines.append(f"  endpoint: {src.get('endpoint', '')}")
        else:
            lines.append(f"  github: {instance.github_url or src.get('github', '')}")
            lines.append("runtime:")
            lines.append(f"  dockerfile: {src.get('dockerfile', 'Dockerfile')}")
            lines.append(f"  port: {src.get('port', instance.port)}")
        return "\n".join(lines)

    def get_nodes(self, instance):
        cache = instance.manifest_cache or {}
        nodes = cache.get("nodes", [])
        return [
            {
                "type": n.get("type"),
                "title": n.get("titleFallback") or n.get("title") or n.get("type", ""),
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
            "is_default",
            "manifest_cache",
            "manifest_fetched_at",
            "created_at",
            "updated_at",
            "docs",
            "nodes",
            "source",
            "module_yaml",
        ]
        read_only_fields = ["id", "manifest_cache", "manifest_fetched_at", "created_at", "updated_at"]


class CreateModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleModel
        fields = ["slug", "name", "description", "icon", "github_url", "image", "port", "auth_token", "active", "is_default"]


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
