from django.shortcuts import get_object_or_404, render, redirect
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone
from knox.models import AuthToken

from accounts.models import Administrator, AdministratorAccessAudit
from sinel_web.utils.decorators import superuser_only
from sinel_web.utils.redirects import get_safe_redirect_url, redirect_back


class LoginView(View):
    template_name = "accounts/login.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        email_address = request.POST.get("email_address")
        password = request.POST.get("password")
        remember_me = True if request.POST.get("remember_me") else False

        user = authenticate(email_address=email_address, password=password)

        if user and user.is_active and user.is_staff:
            login(request, user)
            if remember_me:
                request.session.set_expiry(86400 * 30)
            user.last_login_at = timezone.now()
            user.save()
            redirect_url = get_safe_redirect_url(
                request,
                request.GET.get("next"),
                "dashboard:index",
            )
            return redirect(redirect_url)

        messages.add_message(request, messages.ERROR, "Invalid credentials")
        return render(request, self.template_name)


class AdministratorsView(View):
    template_name = "accounts/administrators.html"

    @method_decorator(superuser_only())
    def get(self, request, *args, **kwargs):
        context = {"administrators": Administrator.objects.all().order_by("-id")}
        return render(request, self.template_name, context)


class AdministratorDetailsView(View):
    template_name = "accounts/administrator_details.html"

    @method_decorator(superuser_only())
    def get(self, request, admin_id, *args, **kwargs):
        context = {
            "administrator": get_object_or_404(Administrator, id=admin_id),
            "role_choices": [
                choice
                for choice in Administrator.Role.choices
                if choice[0] != Administrator.Role.SUPER_ADMIN
            ],
        }
        return render(request, self.template_name, context)

    @method_decorator(superuser_only())
    @transaction.atomic
    def post(self, request, admin_id, *args, **kwargs):
        admin = get_object_or_404(Administrator, id=admin_id)
        photo = request.FILES.get("photo")
        fullname = request.POST.get("fullname", admin.fullname)
        title = request.POST.get("title", admin.title)
        previous_is_active = admin.is_active
        previous_role = admin.role
        requested_role = request.POST.get("role", admin.role)
        allowed_roles = {
            Administrator.Role.FRONT_DESK,
            Administrator.Role.CONTENT_MANAGER,
            Administrator.Role.AUDITOR,
        }
        role_error = False
        status_error = False

        if admin.is_superuser:
            admin.role = Administrator.Role.SUPER_ADMIN
        elif requested_role in allowed_roles:
            admin.role = requested_role
            # Legacy administrator records predate the staff-only dashboard
            # gate. A valid dashboard role must also grant staff access;
            # inactivity remains the separate switch that blocks login.
            admin.is_staff = True
        else:
            role_error = True
            messages.error(request, "Choose a valid dashboard role.")

        if admin.pk == request.user.pk and "is_active" not in request.POST:
            requested_active = admin.is_active
        else:
            requested_active = request.POST.get("is_active") == "on"

        if photo:
            admin.photo = photo
        admin.fullname = fullname
        admin.title = title

        if not requested_active and admin.pk == request.user.pk:
            messages.add_message(
                request,
                messages.ERROR,
                "You cannot deactivate your own account.",
            )
            status_error = True
        elif (
            not requested_active
            and admin.is_superuser
            and not Administrator.objects.filter(
                is_superuser=True,
                is_active=True,
            ).exclude(pk=admin.pk).exists()
        ):
            messages.add_message(
                request,
                messages.ERROR,
                "The last active superuser cannot be deactivated.",
            )
            status_error = True
        else:
            admin.is_active = requested_active

        admin.save()
        if (
            previous_is_active != admin.is_active
            or previous_role != admin.role
        ):
            AdministratorAccessAudit.objects.create(
                administrator=admin,
                changed_by=request.user,
                previous_is_active=previous_is_active,
                new_is_active=admin.is_active,
                previous_role=previous_role,
                new_role=admin.role,
            )

        if previous_is_active and not admin.is_active:
            AuthToken.objects.filter(user=admin).delete()
            messages.success(
                request,
                (
                    f"{admin} was deactivated successfully. "
                    "Dashboard access and existing API sessions were revoked."
                ),
            )
        elif not previous_is_active and admin.is_active:
            messages.success(
                request,
                f"{admin} was activated successfully. Dashboard access was restored.",
            )
        elif not status_error and not role_error:
            messages.success(
                request,
                f"{admin}'s administrator details were updated successfully.",
            )

        if previous_role != admin.role and not role_error:
            messages.success(
                request,
                f"{admin}'s dashboard role was updated to {admin.get_role_display()}.",
            )
        return redirect_back(request, "accounts:administrators")


class CreateAdministrator(View):
    template_name = "accounts/create_administrator.html"

    @method_decorator(superuser_only())
    def get(self, request, *args, **kwargs):
        context = {
            "role_choices": [
                choice
                for choice in Administrator.Role.choices
                if choice[0] != Administrator.Role.SUPER_ADMIN
            ],
        }
        return render(request, self.template_name, context)

    @method_decorator(superuser_only())
    def post(self, request, *args, **kwargs):
        photo = request.FILES.get("photo")
        fullname = request.POST.get("fullname")
        email_address = request.POST.get("email_address")
        title = request.POST.get("title")
        role = request.POST.get(
            "role",
            Administrator.Role.CONTENT_MANAGER,
        )
        is_active = "on" in request.POST.get("is_active", "")
        password = request.POST.get("password")
        repeat_password = request.POST.get("repeat_password")

        if not all((email_address, fullname, title, password, repeat_password)):
            messages.add_message(
                request,
                messages.ERROR,
                "All required fields must be completed.",
            )
            return redirect("accounts:create_administrator")
        if password != repeat_password:
            messages.add_message(request, messages.ERROR,
                                 "Passwords do not match.")
            return redirect("accounts:create_administrator")
        allowed_roles = {
            Administrator.Role.FRONT_DESK,
            Administrator.Role.CONTENT_MANAGER,
            Administrator.Role.AUDITOR,
        }
        if role not in allowed_roles:
            messages.add_message(
                request,
                messages.ERROR,
                "Choose a valid dashboard role.",
            )
            return redirect("accounts:create_administrator")
        try:
            validate_password(password)
            Administrator.objects.create_user(
                email_address=email_address,
                password=password,
                fullname=fullname,
                title=title,
                is_active=is_active,
                is_staff=True,
                is_superuser=False,
                role=role,
                photo=photo,
            )
        except ValidationError as error:
            for message in error.messages:
                messages.add_message(request, messages.ERROR, message)
            return redirect("accounts:create_administrator")
        except IntegrityError:
            messages.add_message(
                request,
                messages.ERROR,
                "An administrator with this email address already exists.",
            )
            return redirect("accounts:create_administrator")

        messages.success(
            request,
            f"{fullname} was created successfully as {dict(Administrator.Role.choices)[role]}.",
        )
        return redirect("accounts:administrators")


class LogoutView(View):
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect("website:index")


class ChangePasswordView(View):
    @method_decorator(superuser_only())
    def post(self, request, *args, **kwargs):
        password = request.POST.get("password")
        repeat_password = request.POST.get("repeat_password")
        current_password = request.POST.get("current_password")
        admin_id = request.POST.get("admin_id")

        user_to_change = get_object_or_404(Administrator, id=admin_id)
        loggedin_user = authenticate(email_address=request.user.email_address,
                                     password=current_password)

        if not loggedin_user:
            messages.add_message(request, messages.ERROR,
                                 "Invalid credentials")
        elif not password or not repeat_password:
            messages.add_message(
                request,
                messages.ERROR,
                "A new password and confirmation are required.",
            )
        elif password != repeat_password:
            messages.add_message(request, messages.ERROR,
                                 "Passwords do not match.")
        else:
            try:
                validate_password(password, user_to_change)
            except ValidationError as error:
                for message in error.messages:
                    messages.add_message(request, messages.ERROR, message)
            else:
                user_to_change.set_password(password)
                user_to_change.save(update_fields=["password", "updated_at"])
                AuthToken.objects.filter(user=user_to_change).delete()
                if request.user.pk == user_to_change.pk:
                    update_session_auth_hash(request, user_to_change)
                messages.add_message(
                    request,
                    messages.SUCCESS,
                    "Password updated successfully.",
                )
        return redirect_back(request, "accounts:administrators")
