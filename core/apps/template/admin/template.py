from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.template.models import TemplateModel, UserTemplateModel
from django.db import models
from unfold.contrib.forms.widgets import WysiwygWidget

from core.apps.template.models.template import TemplateCategoryModel, TemplateFeatureModel, TemplateLikeModel


@admin.register(TemplateModel)
class TemplateAdmin(ModelAdmin):
    # readonly_fields = ["flow"]
    search_fields = ["name"]
    autocomplete_fields = [
        "categories",
        "features",
    ]
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }
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


@admin.register(TemplateFeatureModel)
class TemplateFeatureAdmin(ModelAdmin):
    search_fields = ["name"]
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }
    list_display = (
        "id",
        "__str__",
    )


@admin.register(TemplateCategoryModel)
class TemplateCategoryAdmin(ModelAdmin):
    search_fields = ["name"]
    list_display = (
        "id",
        "__str__",
    )


@admin.register(TemplateLikeModel)
class TemplateLikeAdmin(ModelAdmin):
    list_display = (
        "id",
        "__str__",
    )
