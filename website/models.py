import re
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError
from django.db import models
from accounts.models import Administrator
from django_ckeditor_5.fields import CKEditor5Field
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator


class Contact(models.Model):
    gps = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.CharField(max_length=100)
    telephone = models.CharField(max_length=100)
    lat_lng = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.address


class SocialMediaLink(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="uploads/images")
    link = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class InsurancePartner(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    logo = models.URLField(max_length=200)
    visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Album(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    def get_size(self):
        return self.children.count()


class Media(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    album = models.ForeignKey(Album,
                              related_name="children",
                              on_delete=models.CASCADE)
    media_type = models.CharField(max_length=20, default="image")
    file = models.FileField(max_length=200, upload_to="uploads/images")
    visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name

    @property
    def display_name(self):
        return self.name.replace("-", " ")


class HealthTips(models.Model):
    title = models.CharField(max_length=100)
    slug = models.CharField(max_length=100)
    content = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Banner(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True, null=True)
    url = models.URLField(
        "External button URL",
        max_length=200,
        blank=True,
        null=True,
        help_text="Optional. A selected service takes priority over this URL.",
    )
    service = models.ForeignKey(
        "Service",
        related_name="homepage_banners",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    button_label = models.CharField(
        max_length=50,
        default="Explore our services",
    )
    image = models.ImageField(upload_to="uploads/images")
    visible = models.BooleanField(default=False)
    position = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "-updated_at", "-id")

    def __str__(self) -> str:
        return self.title

    @property
    def button_url(self):
        if self.service_id and self.service.visible:
            return reverse(
                "website:service_details",
                args=[self.service_id],
            )
        return self.url or reverse("website:services")


class Service(models.Model):
    title = models.CharField(max_length=100)
    description = CKEditor5Field()
    schedules = CKEditor5Field(default="")
    doctors = models.ManyToManyField("TeamLead")
    image = models.ImageField(upload_to="uploads/images", )
    visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.title


class HomepageShortcut(models.Model):
    class Icon(models.TextChoices):
        PRIMARY_CARE = "heart-pulse", "Heart pulse"
        HOSPITAL = "hospital", "Hospital"
        PHARMACY = "capsule-pill", "Pharmacy"
        WOMENS_HEALTH = "gender-female", "Women's health"
        FAMILY_CARE = "person-hearts", "Family care"
        EMERGENCY = "activity", "Emergency"
        LABORATORY = "clipboard2-pulse", "Laboratory"
        WELLNESS = "sun", "Wellness"
        PHONE = "telephone", "Telephone"
        PROTECTION = "shield-plus", "Protection"

    class Accent(models.TextChoices):
        SKY = "sky", "Sinel blue"
        NAVY = "navy", "Navy"
        RED = "red", "Emergency red"
        TEAL = "teal", "Teal"
        GOLD = "gold", "Gold"

    class RibbonStyle(models.TextChoices):
        SKY = "sky", "Sinel blue"
        NAVY = "navy", "Navy"
        RED = "red", "Emergency red"
        TEAL = "teal", "Teal"
        GOLD = "gold", "Gold"

    class RibbonPosition(models.TextChoices):
        RIGHT = "right", "Top right"
        LEFT = "left", "Top left"

    service = models.ForeignKey(
        Service,
        related_name="homepage_shortcuts",
        on_delete=models.CASCADE,
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Leave blank to use the service title.",
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Leave blank to use a short excerpt from the service.",
    )
    icon = models.CharField(
        max_length=30,
        choices=Icon.choices,
        default=Icon.PRIMARY_CARE,
    )
    accent = models.CharField(
        max_length=20,
        choices=Accent.choices,
        default=Accent.SKY,
    )
    ribbon_text = models.CharField(
        max_length=24,
        blank=True,
        help_text=(
            "Optional. Try New, Featured, Popular, 24/7, or add your own."
        ),
    )
    ribbon_style = models.CharField(
        max_length=20,
        choices=RibbonStyle.choices,
        default=RibbonStyle.SKY,
    )
    ribbon_position = models.CharField(
        max_length=10,
        choices=RibbonPosition.choices,
        default=RibbonPosition.RIGHT,
    )
    position = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first.",
    )
    visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "id")

    def __str__(self) -> str:
        return self.display_label

    @property
    def display_label(self):
        return self.label or self.service.title

    @property
    def display_description(self):
        if self.description:
            return self.description
        return Truncator(strip_tags(self.service.description)).words(18)

    @property
    def service_url(self):
        return reverse(
            "website:service_details",
            args=[self.service_id],
        )


class HomepageVideo(models.Model):
    eyebrow = models.CharField(
        max_length=60,
        default="Inside Sinel",
    )
    title = models.CharField(max_length=150)
    description = models.TextField(
        blank=True,
        help_text="A short introduction shown beside the video.",
    )
    youtube_url = models.URLField(
        max_length=300,
        help_text="Use a YouTube watch, share, Shorts, or embed URL.",
    )
    poster = models.ImageField(
        upload_to="uploads/videos",
        blank=True,
        null=True,
        help_text="Recommended: a 16:9 landscape image.",
    )
    poster_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Optional fallback when no poster has been uploaded.",
    )
    visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")

    def __str__(self) -> str:
        return self.title

    @property
    def youtube_id(self):
        parsed = urlparse(self.youtube_url)
        hostname = (parsed.hostname or "").lower()
        video_id = ""

        if hostname in {"youtu.be", "www.youtu.be"}:
            video_id = parsed.path.strip("/").split("/")[0]
        elif hostname in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtube-nocookie.com",
            "www.youtube-nocookie.com",
        }:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif parsed.path.startswith(("/embed/", "/shorts/")):
                video_id = parsed.path.strip("/").split("/")[1]

        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            return video_id
        return ""

    @property
    def embed_url(self):
        if not self.youtube_id:
            return ""
        return (
            "https://www.youtube.com/embed/"
            f"{self.youtube_id}"
        )

    @property
    def thumbnail_url(self):
        if not self.youtube_id:
            return ""
        return f"https://i.ytimg.com/vi/{self.youtube_id}/hqdefault.jpg"

    @property
    def display_poster_url(self):
        if (
            self.poster
            and self.poster.name
            and self.poster.storage.exists(self.poster.name)
        ):
            return self.poster.url
        return self.poster_url or self.thumbnail_url

    def clean(self):
        super().clean()
        if self.youtube_url and not self.youtube_id:
            raise ValidationError(
                {
                    "youtube_url": (
                        "Enter a valid YouTube video URL."
                    )
                }
            )


class Client(models.Model):
    title = models.CharField(max_length=30)
    story = models.TextField()
    image = models.ImageField(upload_to="uploads/images", )
    visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OpeningHour(models.Model):
    days = models.CharField(max_length=100)
    time = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TeamLead(models.Model):
    fullname = models.CharField(max_length=100)
    bio = models.TextField()
    linkedin = models.URLField(blank=True, null=True, default="")
    title = models.CharField(max_length=500)
    photo = models.ImageField(upload_to="uploads/images", )
    visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def display_bio(self):
        bio = self.bio.strip()
        if bio == ".":
            return ""
        return bio.lstrip(".").strip()

    @property
    def public_linkedin_url(self):
        if not self.linkedin:
            return ""
        parsed = urlparse(self.linkedin)
        hostname = (parsed.hostname or "").lower()
        if (
            hostname in {"linkedin.com", "www.linkedin.com"}
            and parsed.path.startswith("/in/")
        ):
            return self.linkedin
        return ""


class About(models.Model):
    overview = CKEditor5Field()
    mission = CKEditor5Field()
    vision = CKEditor5Field()
    value = CKEditor5Field()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Award(models.Model):
    title = models.CharField(max_length=150)
    issuer = models.CharField(
        max_length=150,
        blank=True,
        help_text="Optional organisation or programme that issued it.",
    )
    year = models.PositiveSmallIntegerField(blank=True, null=True)
    description = models.TextField(
        blank=True,
        help_text="Optional context visitors should know.",
    )
    image = models.ImageField(
        upload_to="uploads/awards",
        blank=True,
        null=True,
    )
    image_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Optional fallback when no image has been uploaded.",
    )
    position = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first.",
    )
    visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "-year", "id")

    def __str__(self) -> str:
        return self.title

    @property
    def display_image_url(self):
        if (
            self.image
            and self.image.name
            and self.image.storage.exists(self.image.name)
        ):
            return self.image.url
        return self.image_url

    @property
    def display_meta(self):
        return " · ".join(
            str(value)
            for value in (self.issuer, self.year)
            if value
        )

    @property
    def public_title(self):
        if re.fullmatch(
            r"Sinel Hospital recognition \d+",
            self.title,
            flags=re.IGNORECASE,
        ):
            return "Award & Achievement"
        return self.title

    def clean(self):
        super().clean()
        if not self.image and not self.image_url:
            raise ValidationError(
                {
                    "image": (
                        "Upload an award image or provide an image URL."
                    )
                }
            )


class Testimonial(models.Model):
    username = models.CharField(max_length=100)
    message = models.TextField()
    photo = models.ImageField(upload_to="uploads/images",
                              null=True,
                              blank=True)
    added_by = models.ForeignKey(Administrator,
                                 null=True,
                                 blank=True,
                                 on_delete=models.SET_NULL)
    service = models.ForeignKey(Service,
                                null=True,
                                blank=True,
                                related_name="testimonials",
                                on_delete=models.SET_NULL)
    doctor = models.ForeignKey(TeamLead,
                               null=True,
                               blank=True,
                               on_delete=models.SET_NULL)
    visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.username


class Partner(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField()
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100)
    website = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    visible = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name


class Notification(models.Model):
    title = models.CharField(max_length=100)
    message = models.TextField()
    url = models.URLField(max_length=200, default="", blank=True, null=True)
    expires_at = models.DateTimeField()
    available_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    content_hash = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs) -> None:
        self.content_hash = hash(self.title + self.message)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title
