from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from core.apps.api.models import DebugModel, EnviromentModel, ProjectModel, RelaseModel


class DebugInline(TabularInline):
    model = DebugModel
    tab = True
    fields = ["flow_hash", "service_id", "status"]


class InlineRelease(TabularInline):
    mode = RelaseModel
    tab = True


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
