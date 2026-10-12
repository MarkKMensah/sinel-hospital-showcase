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


class AboutContentForm(forms.ModelForm):
    def save(self, commit=True):
        about = super().save(commit=False)
        if commit:
            if about.pk:
                # Each editor owns only its validated fields, not another
                # editor's concurrently saved introduction or rich-text section.
                about.save(update_fields=set(self.fields) | {"updated_at"})
            else:
                about.save()
            self.save_m2m()
        return about


class AboutForm(AboutContentForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Legacy API clients send only the four rich-text sections. Omitted
        # introduction fields must retain their saved values/defaults.
        if self.is_bound:
            for name in About.HERO_DEFAULTS:
                if name not in self.data:
                    self.fields.pop(name, None)

    class Meta:
        model = About
        exclude = [
            "id",
            "created_at",
            "update_at",
        ]


class AboutHeroForm(AboutContentForm):
    class Meta:
        model = About
        fields = list(About.HERO_DEFAULTS)
        widgets = {
            "hero_description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            limit = About._meta.get_field(name).max_length
            field.help_text = f"Up to {limit} characters. Plain text only."
            field.widget.attrs.update({
                "class": "form-control",
                "maxlength": limit,
                "aria-describedby": (
                    f"id_{name}_help id_{name}_count id_{name}_error"
                ),
                "data-about-character-limit": limit,
            })


class AboutOverviewForm(AboutContentForm):
    class Meta:
        model = About
        fields = ["overview"]
        widgets = {"overview": rich_text_widget()}


class AboutMissionForm(AboutContentForm):
    class Meta:
        model = About
        fields = ["mission"]
        widgets = {"mission": rich_text_widget()}


class AboutVisionForm(AboutContentForm):
    class Meta:
        model = About
        fields = ["vision"]
        widgets = {"vision": rich_text_widget()}


class AboutValueForm(AboutContentForm):
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
            "eyebrow",
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
            "eyebrow": forms.TextInput(attrs={"class": "form-control"}),
            "title": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
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

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "image"):
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Choose an image smaller than 5 MB.")
            if image.image.format not in {"JPEG", "PNG", "WEBP"}:
                raise forms.ValidationError("Choose a JPEG, PNG, or WebP image.")
        return image


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
    class TeamLeadField(forms.ModelMultipleChoiceField):
        def clean(self, value):
            if isinstance(value, (list, tuple)):
                for selected_id in value:
                    try:
                        selected_id_int = int(selected_id)
                    except (TypeError, ValueError):
                        raise forms.ValidationError(
                            self.error_messages["invalid_pk_value"],
                            code="invalid_pk_value",
                            params={"pk": selected_id},
                        )
                    if not 1 <= selected_id_int <= 9223372036854775807:
                        raise forms.ValidationError(
                            self.error_messages["invalid_choice"],
                            code="invalid_choice",
                            params={"value": selected_id},
                        )
            return super().clean(value)

    doctors = TeamLeadField(
        queryset=TeamLead.objects.none(),
        required=False,
        label="Team Lead",
        help_text=(
            "Optional. Select one or more team members with Ctrl (Windows) or "
            "Command (Mac). Hold the same key and click a selected name to remove "
            "it. Existing hidden assignments are marked and remain hidden on the website."
        ),
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = TeamLead.objects.filter(visible=True)
        if self.instance.pk:
            # Preserve existing hidden assignments without offering other hidden leads.
            choices = choices | TeamLead.objects.filter(
                pk__in=self.instance.doctors.values_list("pk", flat=True)
            )
        self.fields["doctors"].queryset = choices.distinct().order_by("fullname", "pk")
        self.fields["doctors"].label_from_instance = self.team_lead_label

    @staticmethod
    def team_lead_label(team_lead):
        if not team_lead.visible:
            return f"{team_lead.fullname} (hidden)"
        return team_lead.fullname

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
