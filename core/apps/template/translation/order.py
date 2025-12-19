from modeltranslation.translator import TranslationOptions, register

from core.apps.template.models import TemplateOrderModel


@register(TemplateOrderModel)
class TemplateOrderTranslation(TranslationOptions):
    fields = []
