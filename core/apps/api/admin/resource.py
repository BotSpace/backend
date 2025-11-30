from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.api.models.resource import ResourceModel, StorageResourceModel


@admin.register(ResourceModel)
class ResourceAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )


@admin.register(StorageResourceModel)
class StorageresourceAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )
