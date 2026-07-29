from blog.models import Page
from website.models import Contact, Notification, Service, Testimonial
from django.core.exceptions import PermissionDenied
from django.utils import timezone


class DashboardAuthorizationMiddleware:
    """Enforce dashboard roles independently of the visible navigation."""

    appointment_view_names = {"appointments"}
    appointment_manage_names = {
        "appointment_update",
        "appointments_export",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        if not (
            user.is_authenticated
            and user.is_active
            and user.is_staff
        ):
            return None

        match = request.resolver_match
        if match and match.namespace == "dashboard":
            if user.is_superuser or match.url_name == "index":
                return None

            if match.url_name in self.appointment_manage_names:
                if not user.can_manage_appointments:
                    raise PermissionDenied
                return None

            if match.url_name in self.appointment_view_names:
                if not user.can_view_appointments:
                    raise PermissionDenied
                return None

            if request.method in {"GET", "HEAD", "OPTIONS"}:
                if not user.can_view_content:
                    raise PermissionDenied
            elif not user.can_manage_content:
                raise PermissionDenied

        if request.path_info.startswith("/ckeditor5/"):
            if not user.can_manage_content:
                raise PermissionDenied

        return None


class CustomMiddleWares(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.contact = Contact.objects.first()
        request.notification = Notification.objects.filter(
            available_at__lte=timezone.now(),
            expires_at__gt=timezone.now()).order_by("-updated_at").first()
        request.pages = Page.objects.filter(visible=True).order_by("title")[:5]
        request.services = Service.objects.filter(visible=True).order_by("title")
        request.testimonials = Testimonial.objects.filter(visible=True)
        return self.get_response(request)
