from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import Post, Page
from website.rich_content import RichContentFormMixin


def rich_text_widget():
    return CKEditor5Widget(
        attrs={"class": "django_ckeditor_5"},
        config_name="extends",
    )


class PostForm(RichContentFormMixin, forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "content", "thumbnail", "tags", "visible"]
        widgets = {"content": rich_text_widget()}


class PageForm(RichContentFormMixin, forms.ModelForm):
    class Meta:
        model = Page
        fields = ["title", "content", "visible"]
        widgets = {"content": rich_text_widget()}
