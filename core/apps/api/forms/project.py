from django import forms

from core.apps.api.models import EnviromentModel, RelaseModel, ResourceModel


class RelaseForm(forms.ModelForm):

    class Meta:
        model = RelaseModel
        fields = "__all__"


class EnviromentForm(forms.ModelForm):

    class Meta:
        model = EnviromentModel
        fields = "__all__"


class ResourceForm(forms.ModelForm):

    class Meta:
        model = ResourceModel
        fields = "__all__"
