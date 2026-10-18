"""Bounded editorial copy for established public sections, not a page builder."""

from dataclasses import dataclass
from html import unescape
from types import SimpleNamespace

from django import forms
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import Truncator
from .rich_content import sanitize_rich_html


@dataclass(frozen=True)
class SectionSpec:
    group: str
    label: str
    eyebrow: str = ""
    title: str = ""
    body: str = ""
    eyebrow_limit: int = 60
    title_limit: int = 110
    body_limit: int = 420
    image: bool = False


SECTION_REGISTRY = {
    "home_services": SectionSpec("Homepage", "Service shortcuts", "Care made easier", "Find the right service", "Choose a service to see schedules, specialists and care information."),
    "home_story": SectionSpec("Homepage", "Hospital story", "Care that grows with you", "A family hospital built around people", body_limit=0, image=True),
    "home_partners": SectionSpec("Homepage", "Partner introduction", "Trusted relationships", "Working together for better care", "Organisations helping us make quality healthcare easier to access."),
    "home_team": SectionSpec("Homepage", "Team introduction", "Experienced professionals", "Meet our care team", body_limit=0),
    "home_news": SectionSpec("Homepage", "News introduction", "Health information", "Latest from Sinel", body_limit=0),
    "shared_testimonials": SectionSpec("Shared sections", "Patient testimonials", "Patient voices", "What they say about us", "Real experiences shared by patients and families we have cared for."),
    "shared_service_testimonials": SectionSpec("Shared sections", "Service testimonials", "Patient experiences", "What our patients say", "Experiences related to this service."),
    "about_highlight_family": SectionSpec("About", "Family care highlight", title="Family-centred", body="Care designed around people, families and every stage of life.", eyebrow_limit=0, title_limit=45, body_limit=150),
    "about_highlight_specialist": SectionSpec("About", "Specialist care highlight", title="Specialist access", body="Experienced teams working together across a broad range of services.", eyebrow_limit=0, title_limit=45, body_limit=150),
    "about_highlight_availability": SectionSpec("About", "Availability highlight", title="Always available", body="Round-the-clock support, including weekends and public holidays.", eyebrow_limit=0, title_limit=45, body_limit=150),
    "about_intro": SectionSpec("About", "Overview introduction", "Welcome to Sinel", "Healthcare built around your wellbeing", body_limit=0),
    "about_principles": SectionSpec("About", "Principles introduction", "What guides us", "Our story, focus and people", "The commitments shaping how we serve every patient and family."),
    "about_awards": SectionSpec("About", "Awards introduction", "Recognition", "Awards & Achievements", "We are honoured to be recognised for our commitment to dependable, compassionate healthcare."),
    "about_cta": SectionSpec("About", "Closing invitation", "Your health, our focus", "Let’s take the next step together", "Talk with our team about the care or specialist support you need."),
    "contact_intro": SectionSpec("Contact", "Page introduction", "Contact Sinel", "Care is close at hand", "Our hospital operates around the clock, every day of the year. Call, message or visit us whenever you need support."),
    "contact_options": SectionSpec("Contact", "Contact options introduction", "Reach our team", "Choose what works for you", "Direct access to the hospital team, wherever you are."),
    "contact_location": SectionSpec("Contact", "Location introduction", "Visit the hospital", "Find us in Tema", "Tema, Ghana", body_limit=80),
    "contact_cta": SectionSpec("Contact", "Booking invitation", "Planning your visit?", "Save time by requesting an appointment", "Share a few details and our team will help coordinate the next step."),
    "gallery_intro": SectionSpec("Gallery", "Page introduction", "Our Gallery", "Inside Sinel", "Meet the people, facilities and everyday moments behind the compassionate specialist care we provide."),
    "gallery_collection": SectionSpec("Gallery", "Collection introduction", "A closer look", "People and places at Sinel", "Select any photograph to see it in a larger, distraction-free view."),
    "team_intro": SectionSpec("Team", "Page introduction", "Our people", "People behind your care", "Meet the clinical specialists, care teams and operational professionals working together to make every Sinel experience safe, personal and dependable."),
    "team_directory": SectionSpec("Team", "Directory introduction", "Team directory", "Find the right person for your care", "Search by name or narrow the directory by specialty and department."),
    "partners_intro": SectionSpec("Partners", "Page introduction", "Our partner network", "Better health happens together", "We work with insurers, businesses and community organisations to make dependable healthcare more accessible for the people we serve."),
    "partners_panel": SectionSpec("Partners", "Logo panel introduction", title="Trusted network", body="Supporting coordinated care, convenient access and healthier communities.", eyebrow_limit=0, title_limit=60, body_limit=180),
    "partners_directory": SectionSpec("Partners", "Directory introduction", "Partner directory", "Organisations in our care network", "Explore the organisations working with Sinel Hospital across healthcare access, employee wellbeing and community support."),
    "partners_cta": SectionSpec("Partners", "Partnership invitation", "Work with Sinel", "Interested in becoming a partner?", "Let’s explore how we can improve access to trusted healthcare together."),
    "services_intro": SectionSpec("Services", "Page introduction", "Comprehensive specialist care", "Healthcare services for every stage of life", "Our experienced teams provide timely, coordinated care—from routine consultations and diagnostics to specialist treatment and emergency support."),
    "services_directory": SectionSpec("Services", "Directory introduction", "Explore our care", "Our services", "Select a service for schedules, specialists and detailed care information."),
    "service_intro": SectionSpec("Services", "Service detail introduction", "Sinel specialist care", body="Speak with our team to understand the right next step for your care.", title_limit=0),
    "service_description": SectionSpec("Services", "Service description heading", "About this service", "How we can help", body_limit=0),
    "service_team": SectionSpec("Services", "Service team heading", "Your care team", "Specialists for this service", body_limit=0),
    "news_intro": SectionSpec("News", "Page introduction", "Health, care and community", "Ideas for healthier lives", "Hospital news, practical health guidance and stories from the people shaping care at Sinel."),
    "booking_intro": SectionSpec("Appointments", "Page introduction", "Plan your visit", "Request an appointment", body_limit=0),
    "booking_guidance": SectionSpec("Appointments", "Booking guidance", title="A simple way to get started", body="Choose your preferred date and time in one field. A member of the Sinel team will follow up to confirm availability.", eyebrow_limit=0),
}

METADATA_ROUTES = {
    "home": ("Homepage", "website:index", "home_story"),
    "about": ("About", "website:about", "about_intro"),
    "contact": ("Contact", "website:contact", "contact_intro"),
    "gallery": ("Gallery", "website:gallery", "gallery_intro"),
    "team": ("Team", "website:doctors", "team_intro"),
    "partners": ("Partners", "website:partners", "partners_intro"),
    "services": ("Services", "website:services", "services_intro"),
    "news": ("News", "blog:posts", "news_intro"),
    "appointments": ("Appointments", "communications:book_appointment", "booking_intro"),
}


def normalized_copy(value):
    """Plain text uses Unicode code points and single spaces, never truncation."""
    if any(ord(char) < 32 and char not in "\r\n\t" for char in value):
        raise ValidationError("Remove unsupported control characters.")
    return " ".join(value.split())


class PageSection(models.Model):
    key = models.CharField(max_length=60, unique=True)
    eyebrow = models.CharField(max_length=60, blank=True, default="")
    title = models.CharField(max_length=110, blank=True, default="")
    body = models.CharField(max_length=420, blank=True, default="")
    image = models.ImageField(upload_to="uploads/page-content", blank=True, null=True)
    image_alt = models.CharField(max_length=180, blank=True, default="")
    revision = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "website"

    def clean(self):
        super().clean()
        spec = SECTION_REGISTRY.get(self.key)
        if spec is None:
            raise ValidationError({"key": "Choose a supported website section."})
        errors = {}
        for name in ("eyebrow", "title", "body"):
            value = normalized_copy(getattr(self, name))
            limit = getattr(spec, name + "_limit")
            if not limit and value:
                errors[name] = "This section does not use this field."
            elif len(value) > limit:
                errors[name] = f"Use no more than {limit} characters."
            elif limit and name in {"title", "body"} and not value:
                errors[name] = "Enter text for this section."
            setattr(self, name, value)
        if not spec.image and (self.image or self.image_alt):
            errors["image"] = "This section does not use an image."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        spec = SECTION_REGISTRY.get(self.key)
        return f"{spec.group}: {spec.label}" if spec else self.key


class PageMetadata(models.Model):
    key = models.CharField(max_length=30, unique=True)
    title = models.CharField(max_length=70, blank=True, default="")
    description = models.CharField(max_length=160, blank=True, default="")
    revision = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "website"

    def clean(self):
        super().clean()
        if self.key not in METADATA_ROUTES:
            raise ValidationError({"key": "Choose a supported website page."})

    def __str__(self):
        return METADATA_ROUTES.get(self.key, (self.key,))[0]


class ContentConflict(Exception):
    pass


def revision_token(kind, key, record):
    return signing.dumps(
        {"kind": kind, "key": key, "revision": record.revision if record else 0},
        salt="website.editor-revision",
    )


def save_editor_form(form, kind, key):
    """Compare-and-update and unique first insert prevent stale editor overwrites."""
    try:
        expected = signing.loads(form.cleaned_data["revision_token"], salt="website.editor-revision")
        if expected["kind"] != kind or expected["key"] != key:
            raise ValueError
        revision = expected["revision"]
        if not isinstance(revision, int) or revision < 0:
            raise ValueError
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        raise ContentConflict("This form could not be verified. Reload the page and try again.")

    model = form._meta.model
    record = form.save(commit=False)
    record.key = key
    fields = {name: getattr(record, name) for name in form._meta.fields if name in form.fields}
    # Store an upload only after a successful conflict check. File storage is not
    # transactional; never delete or replace the currently referenced asset here.
    with transaction.atomic():
        if revision:
            updated = model.objects.filter(key=key, revision=revision).update(
                revision=F("revision") + 1, updated_at=timezone.now(),
                **{name: value for name, value in fields.items() if name != "image"},
            )
            if not updated:
                raise ContentConflict("Someone saved this section after you opened it. Your changes are below; reload to review the latest text before saving again.")
            if "image" in fields:
                image = fields["image"]
                if image and not image._committed:
                    image.save(image.name, image.file, save=False)
                model.objects.filter(key=key).update(image=image.name if image else "")
        else:
            try:
                with transaction.atomic():
                    image = record.image if "image" in fields else None
                    if "image" in fields:
                        record.image = None
                    record.revision = 1
                    record.save(force_insert=True)
                    if image:
                        if not image._committed:
                            image.save(image.name, image.file, save=False)
                        model.objects.filter(key=key).update(image=image.name)
            except IntegrityError:
                raise ContentConflict("This section was just saved by someone else. Your changes are below; reload to review the latest text.")
    return model.objects.get(key=key)


class CopyFormMixin:
    def add_copy_guidance(self):
        for name, field in self.fields.items():
            if isinstance(field, forms.CharField) and name != "revision_token":
                field.strip = False
                limit = field.max_length
                field.widget.attrs.update({"class": "form-control", "data-copy-limit": limit})
                # HTML maxlength uses UTF-16 units while Python counts code
                # points. The live counter and authoritative server agree.
                field.widget.attrs.pop("maxlength", None)
                field.help_text = f"Up to {limit} characters. Combined emoji can count more than once. Line breaks and extra spaces become single spaces."

    def clean(self):
        cleaned = super().clean()
        for name, value in list(cleaned.items()):
            if name != "revision_token" and isinstance(value, str):
                try:
                    cleaned[name] = normalized_copy(value)
                except ValidationError as exc:
                    self.add_error(name, exc)
        return cleaned


class NormalizedCopyField(forms.CharField):
    def to_python(self, value):
        return normalized_copy(super().to_python(value))


class PageSectionForm(CopyFormMixin, forms.ModelForm):
    revision_token = forms.CharField(max_length=2048, widget=forms.HiddenInput)

    class Meta:
        model = PageSection
        fields = ["eyebrow", "title", "body", "image", "image_alt"]
        widgets = {"body": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, section_key, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.key = section_key
        spec = SECTION_REGISTRY[section_key]
        for name in ("eyebrow", "title", "body"):
            limit = getattr(spec, name + "_limit")
            if not limit:
                self.fields.pop(name)
                continue
            self.fields[name] = NormalizedCopyField(
                max_length=limit, required=name != "eyebrow",
                widget=self.fields[name].widget,
            )
        if not spec.image:
            self.fields.pop("image")
            self.fields.pop("image_alt")
        else:
            self.fields["image"].help_text = "Optional JPG, PNG, WebP or GIF, up to 5 MB and 24 megapixels (6,000 pixels per edge). Clear to use the default image."
            self.fields["image_alt"] = NormalizedCopyField(max_length=180, required=False, label="Image description")
        self.add_copy_guidance()
        if not self.is_bound:
            self.initial["revision_token"] = revision_token("section", section_key, self.instance if self.instance.pk else None)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "content_type"):
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Choose an image no larger than 5 MB.")
            if image.image.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                raise ValidationError("Choose a JPG, PNG, WebP or GIF image.")
            width, height = image.image.size
            if max(width, height) > 6000 or width * height > 24_000_000:
                raise ValidationError("Choose an image up to 6,000 pixels per edge and 24 megapixels.")
        return image


class PageMetadataForm(CopyFormMixin, forms.ModelForm):
    revision_token = forms.CharField(max_length=2048, widget=forms.HiddenInput)

    class Meta:
        model = PageMetadata
        fields = ["title", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, page_key, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.key = page_key
        for name, limit in (("title", 70), ("description", 160)):
            self.fields[name] = NormalizedCopyField(max_length=limit, required=False, widget=self.fields[name].widget)
        self.add_copy_guidance()
        for field in ("title", "description"):
            self.fields[field].help_text += " Leave blank to use the page default."
        if not self.is_bound:
            self.initial["revision_token"] = revision_token("metadata", page_key, self.instance if self.instance.pk else None)


def public_sections():
    result = {
        key: SimpleNamespace(eyebrow=spec.eyebrow, title=spec.title, body=spec.body, image=None, image_alt=spec.title)
        for key, spec in SECTION_REGISTRY.items()
    }
    for row in PageSection.objects.filter(key__in=SECTION_REGISTRY):
        spec = SECTION_REGISTRY[row.key]
        result[row.key] = SimpleNamespace(
            eyebrow=row.eyebrow, title=row.title, body=row.body,
            image=row.image if spec.image else None,
            image_alt=row.image_alt or row.title,
        )
    return result


def metadata_for_request(request):
    fallback = {"title": "Sinel | Your Specialist Family Hospital", "description": "Personalised, professional healthcare at Sinel Specialist Hospital."}
    match = request.resolver_match
    if match is None:
        return fallback
    for key, (label, route, section_key) in METADATA_ROUTES.items():
        if match.view_name == route:
            section = getattr(request, "content", None)
            section = section[section_key] if section is not None else public_sections()[section_key]
            row = PageMetadata.objects.filter(key=key).first()
            return {
                "title": row.title if row and row.title else f"{label} | Sinel Specialist Hospital",
                "description": row.description if row and row.description else section.body or fallback["description"],
            }
    detail_routes = {
        "website:service_details": ("website", "Service", "service_id", "description"),
        "website:static_page_view": ("blog", "Page", "page_id", "content"),
        "blog:post_detail": ("blog", "Post", "post_id", "content"),
    }
    if match.view_name in detail_routes:
        from django.apps import apps
        app, model_name, argument, body_field = detail_routes[match.view_name]
        identifier = str(match.kwargs.get(argument, ""))
        if identifier.isascii() and identifier.isdecimal() and len(identifier) <= 18:
            model = apps.get_model(app, model_name)
            record = model.objects.filter(pk=int(identifier), visible=True).only("title", body_field).first()
            if record:
                return {
                    "title": f"{record.title} | Sinel Specialist Hospital",
                    "description": Truncator(" ".join(unescape(strip_tags(sanitize_rich_html(getattr(record, body_field)))).split())).chars(160),
                }
    return fallback
