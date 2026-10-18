"""One allowlist for saved rich text and legacy HTML at every render boundary.

No historical rows are rewritten on read. New model saves, dashboard forms and
the public template filter use the same policy. Bulk SQL must not be used as an
editorial write path: Django's pre_save signals deliberately do not cover it.
"""

import re
from urllib.parse import urlsplit

import nh3
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models.signals import pre_save


RICH_FIELDS = {
    "website.about": ("overview", "mission", "vision", "value"),
    "website.service": ("description", "schedules"),
    "blog.post": ("content",),
    "blog.page": ("content",),
}

ALLOWED_TAGS = {
    "p", "br", "div", "span", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "del", "sub", "sup",
    "blockquote", "pre", "code", "hr", "a", "ul", "ol", "li",
    "figure", "figcaption", "img", "table", "caption", "colgroup", "col",
    "thead", "tbody", "tfoot", "tr", "th", "td",
}


def safe_rich_destination(value, image=False):
    """No executable, protocol-relative, credentialed or control-filled URLs."""
    if not value or re.search(r"[\x00-\x20\x7f]", value) or "\\" in value:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() in {"http", "https"}:
            parsed.port
            return value if parsed.hostname and not parsed.username and not parsed.password else None
        if not image and parsed.scheme.lower() == "mailto":
            validate_email(parsed.path)
            return value
        if not image and parsed.scheme.lower() == "tel":
            return value if re.fullmatch(r"\+?[0-9()-]{7,25}", parsed.path) else None
        if not parsed.scheme and not parsed.netloc and not value.startswith("//"):
            if image and value.startswith(("#", "?")):
                return None
            return value
    except (ValueError, ValidationError):
        return None
    return None


def safe_rich_style(value):
    """Keep ordinary editor formatting, not layout execution or CSS URLs."""
    choices = {
        "text-align": {"left", "right", "center", "justify", "start", "end"},
        "font-weight": {"normal", "bold", "bolder", "100", "200", "300", "400", "500", "600", "700", "800", "900"},
        "font-style": {"normal", "italic", "oblique"},
        "text-decoration": {"none", "underline", "line-through", "overline"},
        "text-decoration-line": {"none", "underline", "line-through", "overline"},
        "border-collapse": {"collapse", "separate"},
        "border-style": {"none", "solid", "dashed", "dotted", "double"},
    }
    color_names = {"black", "white", "red", "green", "blue", "navy", "teal", "gray", "grey", "yellow", "orange", "brown", "purple", "pink", "transparent", "currentcolor"}
    kept = []
    for declaration in value.split(";"):
        if ":" not in declaration:
            continue
        name, entry = (part.strip().lower() for part in declaration.split(":", 1))
        allowed = entry in choices.get(name, set())
        if name in {"color", "background-color", "border-color"}:
            allowed = entry in color_names or bool(re.fullmatch(r"#(?:[0-9a-f]{3}|[0-9a-f]{4}|[0-9a-f]{6}|[0-9a-f]{8})", entry))
            allowed = allowed or bool(re.fullmatch(r"(?:rgb|rgba|hsl|hsla)\([0-9.,% /+-]+\)", entry))
        elif name == "font-size":
            allowed = entry in {"small", "medium", "large", "x-large", "xx-large"} or bool(re.fullmatch(r"(?:[89]|[1-4][0-9]|50)px", entry))
        elif name in {"width", "height"}:
            match = re.fullmatch(r"([0-9]{1,4})(px|%)", entry)
            allowed = bool(match and 0 < int(match[1]) <= (100 if match[2] == "%" else 1600))
        elif name == "border-width":
            allowed = bool(re.fullmatch(r"[0-5]px", entry))
        if allowed:
            kept.append(f"{name}:{entry}")
    return ";".join(kept) or None


def rich_attribute_filter(tag, attribute, value):
    if attribute in {"href", "src"}:
        return safe_rich_destination(value, image=attribute == "src")
    if attribute == "style":
        return safe_rich_style(value)
    if attribute in {"width", "height", "colspan", "rowspan", "span", "start", "value"}:
        return value if re.fullmatch(r"[0-9]{1,4}", value) and int(value) > 0 else None
    return value


_CLEANER = nh3.Cleaner(
    tags=ALLOWED_TAGS,
    clean_content_tags={"script", "style", "iframe", "object", "embed", "svg", "math", "template", "noscript"},
    attributes={
        "*": {"title", "style"},
        "a": {"href"},
        "img": {"src", "alt", "width", "height"},
        "ol": {"start"}, "li": {"value"},
        "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan", "scope"},
        "col": {"span"},
    },
    tag_attribute_values={"a": {"target": {"_blank", "_self"}}},
    allowed_classes={
        "figure": {"image", "image_resized", "image-style-side", "image-style-align-left", "image-style-align-right", "image-style-align-center", "table"},
        "span": {"text-tiny", "text-small", "text-big", "text-huge"},
    },
    attribute_filter=rich_attribute_filter,
    strip_comments=True,
    link_rel="noopener noreferrer",
    url_schemes={"http", "https", "mailto", "tel"},
)


def sanitize_rich_html(value):
    return _CLEANER.clean(str(value or ""))


class RichContentFormMixin:
    """Sanitize editor values without altering raw-instance revision identity."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fields = RICH_FIELDS.get(self._meta.model._meta.label_lower, ())
        if self.is_bound:
            self.data = self.data.copy()
            for name in fields:
                key = self.add_prefix(name)
                if name in self.fields and key in self.data:
                    self.data[key] = sanitize_rich_html(self.data[key])
        else:
            for name in fields:
                if name in self.fields and name in self.initial:
                    self.initial[name] = sanitize_rich_html(self.initial[name])


def sanitize_model_rich_fields(sender, instance, update_fields=None, raw=False, **kwargs):
    if raw:
        return
    for name in RICH_FIELDS[sender._meta.label_lower]:
        if update_fields is None or name in update_fields:
            setattr(instance, name, sanitize_rich_html(getattr(instance, name)))


def connect_rich_content_signals():
    from django.apps import apps
    for label in RICH_FIELDS:
        pre_save.connect(
            sanitize_model_rich_fields,
            sender=apps.get_model(label),
            dispatch_uid=f"safe-rich-content:{label}",
            weak=False,
        )
