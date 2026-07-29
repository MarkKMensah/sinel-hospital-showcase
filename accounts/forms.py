from django import forms
from .models import Administrator


class AdministratorForm(forms.ModelForm):
    class Meta:
        model = Administrator
        exclude = [
            "id",
            "created_at",
            "groups",
            "update_at",
        ]
