from modeltranslation.translator import TranslationOptions, register

from core.apps.template.models import TemplateModel, UserTemplateModel


@register(TemplateModel)
class TemplateTranslation(TranslationOptions):
    fields = []


@register(UserTemplateModel)
class UsertemplateTranslation(TranslationOptions):
    fields = []
