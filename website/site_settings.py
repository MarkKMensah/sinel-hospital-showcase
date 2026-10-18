"""Business-owned shared details; contact records remain the canonical source."""

import re
from urllib.parse import quote, urlencode, urlsplit

from django import forms
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email
from django.db import IntegrityError, models, transaction
from django.db.models import F, Q
from django.utils import timezone


def validate_public_url(value):
    """Allow ordinary http(s) links only, without executable/obfuscated values."""
    if not value:
        return
    if re.search(r"[\x00-\x20\x7f]", value) or "\\" in value:
        raise ValidationError("Enter a complete http:// or https:// web address.")
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and not parsed.username
            and not parsed.password
        )
        parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise ValidationError("Enter a complete http:// or https:// web address.")
    URLValidator(schemes=["http", "https"])(value)


def normalized_phone(value):
    value = str(value or "")
    if re.search(r"[\x00-\x1f\x7f]", value):
        return ""
    value = value.strip()
    if not re.fullmatch(r"\+?[0-9 ()-]+", value):
        return ""
    digits = re.sub(r"\D", "", value)
    if not 7 <= len(digits) <= 15:
        return ""
    return ("+" if value.startswith("+") else "") + digits


def validate_whatsapp_number(value):
    if value and not normalized_phone(value):
        raise ValidationError(
            "Enter 7–15 digits including the country code, or leave this blank."
        )


class SiteSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    site_key = models.CharField(max_length=20, default="primary", unique=True, editable=False)
    availability_summary = models.CharField(
        "Availability statement", max_length=120, default="Open 24 hours, every day",
        help_text="Displayed with the hospital contact information.",
    )
    facebook_url = models.CharField(
        "Facebook address", max_length=300, blank=True,
        default="https://www.facebook.com/SINELHOSPITALTEMA",
        validators=[validate_public_url],
    )
    instagram_url = models.CharField(
        "Instagram address", max_length=300, blank=True,
        default="https://www.instagram.com/sinelhospital/",
        validators=[validate_public_url],
    )
    youtube_url = models.CharField(
        "YouTube address", max_length=300, blank=True,
        default="https://www.youtube.com/channel/UCdRPeJPD-ixsa1y9zVFkKIQ",
        validators=[validate_public_url],
    )
    whatsapp_number = models.CharField(
        "WhatsApp number", max_length=30, blank=True, default="",
        help_text="Include the country code. Leave blank to use the Contact telephone number.",
        validators=[validate_whatsapp_number],
    )
    revision = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="site_settings_single_record"),
            models.CheckConstraint(condition=Q(site_key="primary"), name="site_settings_primary_key"),
        ]
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"


class StaleSiteSettings(Exception):
    pass


class SiteSettingsForm(forms.ModelForm):
    revision_token = forms.CharField(widget=forms.HiddenInput)
    TOKEN_SALT = "website.site-settings.revision"

    class Meta:
        model = SiteSettings
        fields = [
            "availability_summary", "facebook_url", "instagram_url", "youtube_url",
            "whatsapp_number",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "revision_token":
                continue
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["aria-describedby"] = f"id_{name}_help"
            if field.max_length:
                field.widget.attrs["maxlength"] = field.max_length
            if name.endswith("_url"):
                # Do not silently strip control characters before authoritative validation.
                field.strip = False
                field.widget.attrs["type"] = "url"
                field.help_text = "Full http:// or https:// address. Clear to hide this link."
        if not self.is_bound:
            self.initial["revision_token"] = self.token_for(self.instance)

    @classmethod
    def token_for(cls, instance):
        return signing.dumps(
            {"exists": not instance._state.adding, "revision": instance.revision},
            salt=cls.TOKEN_SALT,
        )

    def clean_revision_token(self):
        value = self.cleaned_data["revision_token"]
        try:
            token = signing.loads(value, salt=self.TOKEN_SALT)
            if (
                type(token.get("exists")) is not bool
                or type(token.get("revision")) is not int
                or token["revision"] < 1
            ):
                raise signing.BadSignature
        except (signing.BadSignature, AttributeError, TypeError):
            raise forms.ValidationError("Reload this page before saving again.")
        return token

    def save(self, commit=True):
        if not commit:
            raise ValueError("Site settings require a revision-checked save.")
        if not self.is_valid():
            raise ValueError("Cannot save invalid site settings.")
        token = self.cleaned_data["revision_token"]
        values = {name: self.cleaned_data[name] for name in self.Meta.fields}
        with transaction.atomic():
            if token["exists"]:
                changed = SiteSettings.objects.filter(
                    pk=1, revision=token["revision"],
                ).update(**values, revision=F("revision") + 1, updated_at=timezone.now())
                if changed != 1:
                    raise StaleSiteSettings
            else:
                try:
                    with transaction.atomic():
                        SiteSettings.objects.create(id=1, **values)
                except IntegrityError as error:
                    raise StaleSiteSettings from error
        self.instance = SiteSettings.objects.get(pk=1)
        return self.instance


def _safe_url(value):
    try:
        validate_public_url(value)
    except (ValidationError, TypeError, ValueError):
        return ""
    return value


def _map_query(contact):
    raw = str(getattr(contact, "lat_lng", "") or "").strip()
    match = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*", raw)
    if match:
        lat, lng = map(float, match.groups())
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return f"{match.group(1)},{match.group(2)}"
    return str(getattr(contact, "address", "") or "").strip()


def load_public_site_settings(contact=None, about=None):
    """Read only: opening an editor/public page must never seed persistent rows."""
    result = SiteSettings.objects.filter(pk=1).first() or SiteSettings()
    for name in ("facebook_url", "instagram_url", "youtube_url"):
        setattr(result, name, _safe_url(getattr(result, name)))
    phone = normalized_phone(getattr(contact, "telephone", ""))
    result.telephone_href = f"tel:{phone}" if phone else ""
    whatsapp = normalized_phone(result.whatsapp_number) or phone
    result.whatsapp_url = (
        "https://api.whatsapp.com/send?" + urlencode({"phone": whatsapp.lstrip("+")})
        if whatsapp else ""
    )
    email = str(getattr(contact, "email", "") or "")
    try:
        validate_email(email)
        valid_email = not re.search(r"[\x00-\x20\x7f]", email)
    except ValidationError:
        valid_email = False
    result.email_href = "mailto:" + quote(email, safe="@+.-") if valid_email else ""
    query = _map_query(contact)
    result.directions_url = (
        "https://www.google.com/maps/search/?" + urlencode({"api": "1", "query": query})
        if query else ""
    )
    result.map_embed_url = (
        "https://maps.google.com/maps?" + urlencode({"q": query, "output": "embed"})
        if query else ""
    )
    return result
