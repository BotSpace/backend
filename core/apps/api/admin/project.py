from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from core.apps.api.models import BotModel, DebugModel, EnviromentModel, ProjectModel, RelaseModel


class DebugInline(TabularInline):
    model = DebugModel
    tab = True
    fields = ["flow_hash", "service_id", "status"]


class RelaseAdminTabularInline(admin.TabularInline):
    model = RelaseModel
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProjectModel)
class ProjectAdmin(ModelAdmin):
    inlines = [RelaseAdminTabularInline, DebugInline]
    list_display = (
        "id",
        "__str__",
    )


@admin.register(BotModel)
class BotAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )


@admin.register(DebugModel)
class DebugAdmin(ModelAdmin):
    list_display = ("id", "flow_hash", "service_id", "status")


@admin.register(EnviromentModel)
class EnviromentAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )
