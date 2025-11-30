from django import forms

from core.apps.api.models import ResourceModel


class ResourceForm(forms.ModelForm):

    class Meta:
        model = ResourceModel
        fields = "__all__"
