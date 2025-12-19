from django import forms

from core.apps.payment.models import TransactionModel


class TransactionForm(forms.ModelForm):

    class Meta:
        model = TransactionModel
        fields = "__all__"
