from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.cms.models import CollectionModel, FieldModel


@admin.register(CollectionModel)
class CollectionAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )


@admin.register(FieldModel)
class FieldAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )
