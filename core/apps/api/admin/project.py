from unfold.admin import ModelAdmin

from core.apps.api.models import BotModel, ProjectModel
from django.contrib import admin


@admin.register(ProjectModel)
class ProjectAdmin(ModelAdmin):
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
