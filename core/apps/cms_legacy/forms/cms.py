from django import forms

from core.apps.cms_legacy.models import CollectionModel


class CollectionForm(forms.ModelForm):

    class Meta:
        model = CollectionModel
        fields = "__all__"
