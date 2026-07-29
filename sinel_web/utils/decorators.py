from functools import wraps
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


def _redirect_to_login(request, redirect_url):
    login_url = reverse(redirect_url)
    query = urlencode({"next": request.get_full_path()})
    return redirect(f"{login_url}?{query}")


def superuser_only(redirect_url="accounts:login"):
    """Allow only active superusers to access this view."""

    def decorator(function):
        @wraps(function)
        def wrapper(request, *args, **kwargs):
            if (
                request.user.is_authenticated
                and request.user.is_active
                and request.user.is_superuser
            ):
                return function(request, *args, **kwargs)

            if request.user.is_authenticated:
                raise PermissionDenied

            request.session["error_message"] = "Please login as an administrator."
            return _redirect_to_login(request, redirect_url)

        return wrapper

    return decorator


def staff_only(redirect_url="accounts:login"):
    """Allow only active staff users to access this view."""

    def decorator(function):
        @wraps(function)
        def wrapper(request, *args, **kwargs):
            if (
                request.user.is_authenticated
                and request.user.is_active
                and request.user.is_staff
            ):
                return function(request, *args, **kwargs)

            if request.user.is_authenticated:
                raise PermissionDenied

            request.session["error_message"] = "Please login as an administrator."
            return _redirect_to_login(request, redirect_url)

        return wrapper

    return decorator
