from django import forms

from core.apps.api.models import RelaseModel


class RelaseForm(forms.ModelForm):

    class Meta:
        model = RelaseModel
        fields = "__all__"
