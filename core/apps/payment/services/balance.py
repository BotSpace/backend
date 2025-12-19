from django.contrib.auth import get_user_model

from core.apps.payment.models.history import HistoryModel


User = get_user_model()


def add_balance(user, amount, comment=None):
    """User hisobiga pul qo'shish

    Args:
        user ([TODO:type]): [TODO:description]
        amount ([TODO:type]): [TODO:description]
    """
    user.balance += int(amount)
    user.save()
    HistoryModel.objects.create(
        user=user,
        amount=amount,
        type="income",
        comment=None,
    )


def subtract_balance(user, amount, comment=None):
    """user hisobidan pul yechish

    Args:
        user ([TODO:type]): [TODO:description]
        amount ([TODO:type]): [TODO:description]
    """
    user.balance -= int(amount)
    user.save()
    HistoryModel.objects.create(
        user=user,
        amount=amount,
        type="expense",
        comment=None,
    )
