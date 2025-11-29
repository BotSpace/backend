from django import forms

from core.apps.api.models import FileModel


class FileForm(forms.ModelForm):

    class Meta:
        model = FileModel
        fields = "__all__"
