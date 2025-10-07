from modeltranslation.translator import TranslationOptions, register

from core.apps.api.models import BotModel, ProjectModel, RelaseModel


@register(ProjectModel)
class ProjectTranslation(TranslationOptions):
    fields = []


@register(BotModel)
class BotTranslation(TranslationOptions):
    fields = []


@register(RelaseModel)
class RelaseTranslation(TranslationOptions):
    fields = []
