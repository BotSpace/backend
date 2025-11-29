from modeltranslation.translator import TranslationOptions, register

from core.apps.api.models import FileModel


@register(FileModel)
class FileTranslation(TranslationOptions):
    fields = []
