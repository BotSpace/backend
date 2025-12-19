from django import forms

from core.apps.template.models import TemplateModel, UserTemplateModel


class TemplateForm(forms.ModelForm):

    class Meta:
        model = TemplateModel
        fields = "__all__"


class UsertemplateForm(forms.ModelForm):

    class Meta:
        model = UserTemplateModel
        fields = "__all__"
