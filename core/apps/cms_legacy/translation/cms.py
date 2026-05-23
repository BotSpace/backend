from modeltranslation.translator import TranslationOptions, register

from core.apps.cms_legacy.models import CollectionModel, FieldModel


@register(CollectionModel)
class CollectionTranslation(TranslationOptions):
    fields = []


@register(FieldModel)
class FieldTranslation(TranslationOptions):
    fields = []
