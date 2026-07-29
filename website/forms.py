from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import (
    About,
    Award,
    Banner,
    Client,
    Contact,
    HomepageShortcut,
    HomepageVideo,
    Media,
    Notification,
    OpeningHour,
    Partner,
    Service,
    SocialMediaLink,
    TeamLead,
    Testimonial,
)


def rich_text_widget():
    return CKEditor5Widget(
        attrs={"class": "django_ckeditor_5"},
        config_name="extends",
    )


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]


class AboutForm(forms.ModelForm):
    class Meta:
        model = About
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]


class AboutOverviewForm(forms.ModelForm):
    class Meta:
        model = About
        fields = ["overview"]
        widgets = {"overview": rich_text_widget()}


class AboutMissionForm(forms.ModelForm):
    class Meta:
        model = About
        fields = ["mission"]
        widgets = {"mission": rich_text_widget()}


class AboutVisionForm(forms.ModelForm):
    class Meta:
        model = About
        fields = ["vision"]
        widgets = {"vision": rich_text_widget()}


class AboutValueForm(forms.ModelForm):
    class Meta:
        model = About
        fields = ["value"]
        widgets = {"value": rich_text_widget()}


class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        exclude = [
            "id",
            "media_type",
            "created_at",
            "update_at",
        ]


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = [
            "title",
            "description",
            "image",
            "button_label",
            "service",
            "url",
            "position",
            "visible",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
            ),
            "button_label": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "service": forms.Select(attrs={"class": "form-control"}),
            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com",
                }
            ),
            "position": forms.NumberInput(attrs={"class": "form-control"}),
            "visible": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class HomepageShortcutForm(forms.ModelForm):
    class Meta:
        model = HomepageShortcut
        fields = [
            "service",
            "label",
            "description",
            "icon",
            "accent",
            "ribbon_text",
            "ribbon_style",
            "ribbon_position",
            "position",
            "visible",
        ]
        widgets = {
            "service": forms.Select(attrs={"class": "form-control"}),
            "label": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "icon": forms.Select(attrs={"class": "form-control"}),
            "accent": forms.Select(attrs={"class": "form-control"}),
            "ribbon_text": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "list": "shortcut-ribbon-presets",
                    "placeholder": "Leave blank for no ribbon",
                }
            ),
            "ribbon_style": forms.Select(
                attrs={"class": "form-control"}
            ),
            "ribbon_position": forms.Select(
                attrs={"class": "form-control"}
            ),
            "position": forms.NumberInput(attrs={"class": "form-control"}),
            "visible": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class HomepageVideoForm(forms.ModelForm):
    class Meta:
        model = HomepageVideo
        fields = [
            "eyebrow",
            "title",
            "description",
            "youtube_url",
            "poster",
            "poster_url",
            "visible",
        ]
        widgets = {
            "eyebrow": forms.TextInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "youtube_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://youtu.be/...",
                }
            ),
            "poster": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
            ),
            "poster_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com/poster.jpg",
                }
            ),
            "visible": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class AwardForm(forms.ModelForm):
    class Meta:
        model = Award
        fields = [
            "title",
            "issuer",
            "year",
            "description",
            "image",
            "image_url",
            "position",
            "visible",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "issuer": forms.TextInput(attrs={"class": "form-control"}),
            "year": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1900,
                    "max": 2100,
                }
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control-file"}
            ),
            "image_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com/award.jpg",
                }
            ),
            "position": forms.NumberInput(attrs={"class": "form-control"}),
            "visible": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]
        widgets = {
            "description": rich_text_widget(),
            "schedules": rich_text_widget(),
        }


class TeamLeadForm(forms.ModelForm):
    class Meta:
        model = TeamLead
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]


class OpeningHourForm(forms.ModelForm):
    class Meta:
        model = OpeningHour
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]


class SocialMediaLinkForm(forms.ModelForm):
    class Meta:
        model = SocialMediaLink
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]


class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        exclude = [
            "id",
            "added_by",
            "created_at",
            "update_at",
        ]


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]
