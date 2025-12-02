from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from core.apps.cms.models import CollectionModel, FieldModel, ExportTaskModel


class FieldsInline(TabularInline):
    model = FieldModel
    fields = [
        "name",
        "type",
        "required",
    ]
    extra = 1
    tab = True


@admin.register(CollectionModel)
class CollectionAdmin(ModelAdmin):
    inlines = [FieldsInline]
    list_display = (
        "id",
        "__str__",
    )


@admin.register(ExportTaskModel)
class ExportTaskAdmin(ModelAdmin):
    list_display = (
        "task_id",
        "collection",
        "status",
        "total_records",
        "processed_records",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("task_id", "collection__name")
    readonly_fields = (
        "task_id",
        "created_at",
        "updated_at",
        "file_path",
        "error_message",
        "total_records",
        "processed_records",
    )
