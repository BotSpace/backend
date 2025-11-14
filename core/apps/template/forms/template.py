from django import forms

from core.apps.template.models import TemplateModel


class TemplateForm(forms.ModelForm):

    class Meta:
        model = TemplateModel
        fields = "__all__"
