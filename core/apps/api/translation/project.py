from modeltranslation.translator import TranslationOptions, register

from core.apps.api.models import BotModel, ProjectModel


@register(ProjectModel)
class ProjectTranslation(TranslationOptions):
    fields = []


@register(BotModel)
class BotTranslation(TranslationOptions):
    fields = []
