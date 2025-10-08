from django import forms

from core.apps.api.models import EnviromentModel, RelaseModel


class RelaseForm(forms.ModelForm):

    class Meta:
        model = RelaseModel
        fields = "__all__"


class EnviromentForm(forms.ModelForm):

    class Meta:
        model = EnviromentModel
        fields = "__all__"
