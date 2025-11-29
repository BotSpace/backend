from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from core.apps.api.models import DebugModel, EnviromentModel, ProjectModel, RelaseModel, ResourceModel


class DebugInline(TabularInline):
    model = DebugModel
    tab = True
    fields = ["flow_hash", "service_id", "status"]
    extra = 0


class InlineRelease(TabularInline):
    model = RelaseModel
    tab = True
    extra = 0
    fields = [
        "version",
        "service_id",
        "status",
    ]


class InlineEnviroment(TabularInline):
    model = EnviromentModel
    tab = True


@admin.register(ProjectModel)
class ProjectAdmin(ModelAdmin):
    inlines = [InlineRelease, DebugInline, InlineEnviroment]
    list_display = (
        "id",
        "__str__",
    )


@admin.register(RelaseModel)
class ReleaseAdmin(ModelAdmin):
    list_display = [
        "version",
        "service_id",
        "status",
    ]


@admin.register(ResourceModel)
class ResourceAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )
