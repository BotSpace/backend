from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.api.models import FileModel


@admin.register(FileModel)
class FileAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )
