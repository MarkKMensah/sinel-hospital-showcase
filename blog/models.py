from django.db import models
from django.core.validators import MaxValueValidator
from django.utils.html import strip_tags
from django.utils.text import Truncator

from accounts.models import Administrator
from django_ckeditor_5.fields import CKEditor5Field


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = CKEditor5Field()
    thumbnail = models.ImageField(upload_to="uploads/images")
    tags = models.CharField(max_length=200)
    by = models.ForeignKey(Administrator, on_delete=models.PROTECT)
    visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title

    @property
    def excerpt(self):
        return Truncator(strip_tags(self.content)).words(28)

    @property
    def tag_list(self):
        return [
            tag.strip()
            for tag in self.tags.split(",")
            if tag.strip()
        ]

    @property
    def reading_minutes(self):
        word_count = len(strip_tags(self.content).split())
        return max(1, (word_count + 199) // 200)


class Page(models.Model):
    title = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    content = CKEditor5Field()
    by = models.ForeignKey(Administrator, on_delete=models.PROTECT)
    visible = models.BooleanField(default=False)
    show_in_header = models.BooleanField(default=False)
    show_in_footer = models.BooleanField(default=True)
    menu_label = models.CharField(max_length=60, blank=True, default="")
    menu_position = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(9999)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title

    @property
    def navigation_label(self):
        return self.menu_label or self.title

    def save(self, *args, **kwargs):
        self.slug = "-".join(self.title.lower().split())
        return super().save(*args, **kwargs)
