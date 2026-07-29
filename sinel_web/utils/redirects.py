from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def get_safe_redirect_url(request, candidate, fallback_url_name):
    """Return a local redirect target or a known-safe fallback."""
    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse(fallback_url_name)


def redirect_back(request, fallback_url_name):
    """Redirect to a same-origin referrer when present."""
    target = get_safe_redirect_url(
        request,
        request.META.get("HTTP_REFERER"),
        fallback_url_name,
    )
    return redirect(target)
