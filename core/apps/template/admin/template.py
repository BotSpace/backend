from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.template.models import TemplateModel, UserTemplateModel


@admin.register(TemplateModel)
class TemplateAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )


@admin.register(UserTemplateModel)
class UsertemplateAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )
