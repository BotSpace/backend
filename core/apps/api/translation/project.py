from modeltranslation.translator import TranslationOptions, register

from core.apps.api.models import BotModel, EnviromentModel, ProjectModel, RelaseModel


@register(ProjectModel)
class ProjectTranslation(TranslationOptions):
    fields = []


@register(BotModel)
class BotTranslation(TranslationOptions):
    fields = []


@register(RelaseModel)
class RelaseTranslation(TranslationOptions):
    fields = []


@register(EnviromentModel)
class EnviromentTranslation(TranslationOptions):
    fields = []
