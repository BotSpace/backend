from modeltranslation.translator import TranslationOptions, register

from core.apps.template.models import TemplateModel


@register(TemplateModel)
class TemplateTranslation(TranslationOptions):
    fields = []
