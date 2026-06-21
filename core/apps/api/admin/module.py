from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from core.apps.api.models.module import ModuleModel, ProjectModuleModel


class ProjectModuleInline(TabularInline):
    model = ProjectModuleModel
    tab = True
    extra = 0
    fields = ["project", "enabled", "status", "endpoint", "service_id"]
    readonly_fields = ["status", "endpoint", "service_id"]


@admin.register(ModuleModel)
class ModuleAdmin(ModelAdmin):
    list_display = ["id", "slug", "name", "image", "port", "active", "manifest_fetched_at"]
    list_filter = ["active"]
    search_fields = ["slug", "name"]
    readonly_fields = ["manifest_cache", "manifest_fetched_at", "created_at", "updated_at"]
    inlines = [ProjectModuleInline]
    fieldsets = [
        (None, {"fields": ["slug", "name", "description", "icon", "active"]}),
        ("Deploy", {"fields": ["image", "port", "github_url"]}),
        ("Auth", {"fields": ["auth_token"]}),
        ("Manifest", {"fields": ["manifest_cache", "manifest_fetched_at"]}),
        ("Meta", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(ProjectModuleModel)
class ProjectModuleAdmin(ModelAdmin):
    list_display = ["id", "project", "module", "enabled", "status", "endpoint"]
    list_filter = ["enabled", "status"]
    search_fields = ["module__slug", "project__name"]
    readonly_fields = ["service_id", "endpoint", "created_at", "updated_at"]
