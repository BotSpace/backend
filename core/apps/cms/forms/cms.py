from django import forms

from core.apps.cms.models import CollectionModel


class CollectionForm(forms.ModelForm):

    class Meta:
        model = CollectionModel
        fields = "__all__"
