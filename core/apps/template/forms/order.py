from django import forms

from core.apps.template.models import TemplateOrderModel


class TemplateOrderForm(forms.ModelForm):

    class Meta:
        model = TemplateOrderModel
        fields = "__all__"
