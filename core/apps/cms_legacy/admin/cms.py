from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from core.apps.cms_legacy.models import CollectionModel, FieldModel, ExportTaskModel


class FieldsInline(TabularInline):
    model = FieldModel
    fk_name = "collection"  # Specify which FK to use for inline
    fields = [
        "name",
        "type",
        "required",
        "relation_collection",
    ]
    extra = 1
    tab = True
    autocomplete_fields = ["relation_collection"]


@admin.register(CollectionModel)
class CollectionAdmin(ModelAdmin):
    inlines = [FieldsInline]
    list_display = (
        "id",
        "name",
        "project__name",
        "project__owner__first_name",
        "project__owner__last_name",
        "project__owner__username",
        "project__owner__phone",
    )
    search_fields = ["name"]


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
