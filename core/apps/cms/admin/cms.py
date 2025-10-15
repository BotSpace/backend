from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from core.apps.cms.models import CollectionModel, FieldModel


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
