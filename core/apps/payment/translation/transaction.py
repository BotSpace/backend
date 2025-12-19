from modeltranslation.translator import TranslationOptions, register

from core.apps.payment.models import TransactionModel


@register(TransactionModel)
class TransactionTranslation(TranslationOptions):
    fields = []
