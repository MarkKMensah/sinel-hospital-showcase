from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Post, Page


def rich_text_widget():
    return CKEditor5Widget(
        attrs={"class": "django_ckeditor_5"},
        config_name="extends",
    )


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = [
            "id",
            'by',
            "created_at",
            "update_at",
        ]
        widgets = {"content": rich_text_widget()}


class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        exclude = [
            "id",
            'by',
            "slug",
            "created_at",
            "update_at",
        ]
        widgets = {"content": rich_text_widget()}
