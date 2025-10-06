from core.apps.api.models import FlowModel, RelaseModel
from django import forms


class FlowForm(forms.ModelForm):

    class Meta:
        model = FlowModel
        fields = "__all__"


class RelaseForm(forms.ModelForm):

    class Meta:
        model = RelaseModel
        fields = "__all__"
