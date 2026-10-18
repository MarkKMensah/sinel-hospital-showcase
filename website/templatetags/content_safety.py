from django import template
from django.utils.safestring import mark_safe

from website.rich_content import sanitize_rich_html


register = template.Library()


@register.filter
def rich_content(value):
    """Only allowlisted, sanitized HTML may cross this safe-string boundary."""
    # Reviewed safe-string boundary: only the shared nh3 allowlist output is
    # trusted. Regression/hostile-HTML evidence: website.test_content_safety.
    return mark_safe(sanitize_rich_html(value))  # nosec B308, B703
