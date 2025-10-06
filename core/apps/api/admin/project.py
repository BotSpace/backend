from unfold.admin import ModelAdmin

from core.apps.api.models import BotModel, FlowModel, ProjectModel, RelaseModel
from django.contrib import admin

class RelaseAdminTabularInline(admin.TabularInline):
    model = RelaseModel
    extra = 0
    readonly_fields = ("created_at", "updated_at")

@admin.register(ProjectModel)
class ProjectAdmin(ModelAdmin):
    inlines = [RelaseAdminTabularInline]
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


@admin.register(FlowModel)
class FlowAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )