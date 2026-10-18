import csv
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.forms import FileField
from django.urls import reverse
from django.views.generic import View
from django.utils.decorators import method_decorator
from blog.forms import PageForm, PostForm
from communications.models import (
    Appointment,
    AppointmentExportAudit,
    AppointmentStatusAudit,
)
from sinel_web.utils.decorators import staff_only
from sinel_web.utils.redirects import redirect_back
from website.models import (
    About,
    Album,
    Award,
    Banner,
    Contact,
    HomepageShortcut,
    HomepageVideo,
    Media,
    Notification,
    Partner,
    Service,
    TeamLead,
    Testimonial,
)
from blog.models import Page, Post
from django.contrib import messages
from website.forms import (
    AboutHeroForm,
    AboutMissionForm,
    AboutOverviewForm,
    AboutValueForm,
    AboutVisionForm,
    AlbumForm,
    AwardForm,
    BannerForm,
    ContactForm,
    HomepageShortcutForm,
    HomepageVideoForm,
    MediaForm,
    NotificationForm,
    PartnerForm,
    ServiceForm,
    TeamLeadForm,
    TestimonialForm,
)
from django.utils import timezone
from django.utils.dateparse import parse_date
from accounts.models import Administrator
from .editor_state import (
    CONFLICT_MESSAGE,
    TOKEN_FIELD,
    editor_instance,
    locked_editor_instance,
    revision_matches,
    revision_token,
)


class ContentEditorView(View):
    """Bound editor forms with field-scoped conflict checks and safe recovery."""

    singleton = False
    author_field = None
    derived_fields = ()

    def success_message(self, saved):
        return "Changes saved successfully."

    def context(self, instance, form, token=None):
        if form.is_bound and instance is not None and instance.pk:
            # ModelForm validation/save may replace its in-memory asset reference
            # before persistence succeeds. Only show the durable current asset.
            current = self.model_class.objects.filter(pk=instance.pk).first()
            if current is not None:
                instance = current
                form.instance = current
                for name, field in form.fields.items():
                    if isinstance(field, FileField):
                        form.initial[name] = getattr(current, name)
                        form[name].initial = getattr(current, name)
        for field in form.fields.values():
            if not hasattr(field.widget, "config_name"):
                field.widget.attrs.setdefault("class", "form-check-input" if getattr(field.widget, "input_type", None) == "checkbox" else "form-control")
        reload_url = self.request.path
        if instance is not None and instance.pk and not self.singleton:
            reload_url += "?" + urlencode({self.object_id_field: instance.pk})
        return {
            self.context_name: instance,
            "form": form,
            "editor_revision": token if token is not None else revision_token(
                self.model_class, instance, form.fields
            ),
            "editor_reload_url": reload_url,
        }

    @method_decorator(staff_only())
    def get(self, request, *args, **kwargs):
        instance = (
            self.model_class.objects.first()
            if self.singleton else editor_instance(
                self.model_class, request.GET.get(self.object_id_field)
            )
        )
        return render(request, self.template_name, self.context(
            instance, self.form_class(instance=instance)
        ))

    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        object_id = request.POST.get(self.object_id_field)
        token = request.POST.get(TOKEN_FIELD, "")
        form = None
        instance = None
        try:
            with locked_editor_instance(
                self.model_class, object_id, singleton=self.singleton
            ) as instance:
                form = self.form_class(request.POST, request.FILES or None, instance=instance)
                revision_fields = self.form_class(instance=instance).fields
                if not revision_matches(token, self.model_class, instance, revision_fields):
                    form.is_valid()
                    form.add_error(None, CONFLICT_MESSAGE)
                    return render(request, self.template_name, self.context(instance, form, token), status=409)
                if not form.is_valid():
                    return render(request, self.template_name, self.context(instance, form, token), status=400)
                saved = form.save(commit=False)
                if self.author_field and instance is None:
                    setattr(saved, self.author_field, request.user)
                if instance is not None:
                    owned_fields = {
                        name for name in form.fields
                        if not self.model_class._meta.get_field(name).many_to_many
                    }
                    saved.save(update_fields=owned_fields | set(self.derived_fields) | {"updated_at"})
                else:
                    saved.save()
                form.save_m2m()
        except OSError:
            if form is None:
                raise
            # Query/re-render only after the atomic block has rolled back.
            form.add_error(None, (
                "The file could not be stored. No content changes were saved. "
                "Existing files are unchanged. Select the replacement again and try again."
            ))
            return render(
                request, self.template_name, self.context(instance, form, token), status=503
            )
        messages.success(request, self.success_message(saved))
        if self.context_name == "media":
            return redirect("dashboard:album", album_id=saved.album_id)
        return redirect(self.success_url_name)


def filtered_appointments(request):
    appointments = Appointment.objects.select_related(
        "assigned_to"
    ).order_by("-created_at", "-id")

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    service = request.GET.get("service", "").strip()
    date_from = parse_date(request.GET.get("date_from", ""))
    date_to = parse_date(request.GET.get("date_to", ""))

    if search:
        appointments = appointments.filter(
            Q(fullname__icontains=search)
            | Q(email__icontains=search)
            | Q(number__icontains=search)
            | Q(service__icontains=search)
            | Q(message__icontains=search)
        )
    if status in dict(Appointment.Status.choices):
        appointments = appointments.filter(status=status)
    if service:
        appointments = appointments.filter(service=service)
    if date_from:
        appointments = appointments.filter(created_at__date__gte=date_from)
    if date_to:
        appointments = appointments.filter(created_at__date__lte=date_to)

    return appointments


def spreadsheet_safe(value):
    """Prevent exported patient-provided text from becoming a formula."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


class IndexView(View):
    template_name = "dashboard/index.html"

    @method_decorator(staff_only())
    def get(self, request, *args, **kwargs):
        context = {
            "posts": Post.objects.all(),
            "administrators": Administrator.objects.all(),
            "services": Service.objects.all(),
            "about": About.objects.first()
        }
        return render(request, self.template_name, context)


class AboutView(View):
    template_name = "dashboard/about.html"
    form_classes = {
        "hero": AboutHeroForm,
        "overview": AboutOverviewForm,
        "mission": AboutMissionForm,
        "vision": AboutVisionForm,
        "value": AboutValueForm,
    }

    def get_context(self, about, bound_form=None, section=None, token=None):
        section_forms = {
            name: (
                bound_form
                if name == section and bound_form is not None
                else form_class(instance=about)
            )
            for name, form_class in self.form_classes.items()
        }
        for name, form in section_forms.items():
            form.editor_revision = (
                token if name == section and token is not None
                else revision_token(About, about, form.fields)
            )
        editor_media = section_forms["overview"].media
        for name in ("mission", "vision", "value"):
            editor_media += section_forms[name].media
        return {
            "about": about,
            "hero_form": section_forms["hero"],
            "overview_form": section_forms["overview"],
            "mission_form": section_forms["mission"],
            "vision_form": section_forms["vision"],
            "value_form": section_forms["value"],
            "editor_media": editor_media,
            "active_section": section or "hero",
        }

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        about = About.objects.order_by("pk").first() or About()
        section = request.GET.get("section", "hero")
        if section not in self.form_classes:
            section = "hero"
        return render(
            request, self.template_name, self.get_context(about, section=section)
        )

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        section = request.POST.get("section", "")
        form_class = self.form_classes.get(section)
        if form_class is None:
            messages.error(request, "Choose a valid About section.")
            return redirect("dashboard:about")

        token = request.POST.get(TOKEN_FIELD, "")
        with locked_editor_instance(About, singleton=True) as about:
            about = about or About()
            form = form_class(request.POST, instance=about)
            valid_revision = revision_matches(token, About, about, form.fields)
            valid_form = form.is_valid()
            if not valid_revision or not valid_form:
                if not valid_revision:
                    form.add_error(None, CONFLICT_MESSAGE)
                return render(
                    request, self.template_name,
                    self.get_context(about, bound_form=form, section=section, token=token),
                    status=409 if not valid_revision else 400,
                )
            form.save()
        label = "Page introduction" if section == "hero" else section.title()
        messages.success(request, f"{label} updated successfully.")
        return redirect(reverse("dashboard:about") + "?section=" + section)


class AwardsView(View):
    template_name = "dashboard/awards.html"

    @method_decorator(staff_only())
    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {"awards": Award.objects.all()},
        )


class CreateUpdateAwardView(ContentEditorView):
    template_name = "dashboard/create_update_award.html"
    form_class = AwardForm
    model_class = Award
    object_id_field = "award_id"
    context_name = "award"
    success_url_name = "dashboard:awards"

    def success_message(self, saved):
        return f'Award "{saved.title}" was saved successfully.'


class DeleteAwardView(View):
    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        award = get_object_or_404(
            Award,
            id=request.POST.get("award_id"),
        )
        title = award.title
        award.delete()
        messages.success(
            request,
            f'Award "{title}" was removed.',
        )
        return redirect("dashboard:awards")


class ContactView(ContentEditorView):
    template_name = "dashboard/contact.html"
    form_class = ContactForm
    model_class = Contact
    context_name = "contact"
    object_id_field = "contact_id"
    singleton = True
    success_url_name = "dashboard:contact"


class GalleryView(View):
    template_name = "dashboard/gallery.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {"albumns": Album.objects.all()}
        return render(request, self.template_name, context)


class AlbumView(View):
    template_name = "dashboard/album_items.html"

    @method_decorator(staff_only())
    def get(self, request, album_id, *argd, **kwargs):
        album = get_object_or_404(Album, id=album_id)
        context = {"album": album}
        return render(request, self.template_name, context)


class CreateUpdateAlbum(ContentEditorView):
    template_name = "dashboard/create_update_album.html"
    form_class = AlbumForm
    model_class = Album
    object_id_field = "album_id"
    context_name = "album"
    success_url_name = "dashboard:gallery"


class DeleteAlbumView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        album_id = request.POST.get("album_id")
        Album.objects.filter(id=album_id).delete()
        return redirect_back(request, "dashboard:index")


class CreateUpdateMedia(ContentEditorView):
    template_name = "dashboard/create_update_media.html"
    form_class = MediaForm
    model_class = Media
    object_id_field = "media_id"
    context_name = "media"


class DeleteMediaView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        media_id = request.POST.get("media_id")
        Media.objects.filter(id=media_id).delete()
        return redirect_back(request, "dashboard:index")


class ServicesView(View):
    template_name = "dashboard/services.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {"services": Service.objects.all()}
        return render(request, self.template_name, context)


class CreateUpdateService(ContentEditorView):
    template_name = "dashboard/create_update_service.html"
    form_class = ServiceForm
    model_class = Service
    object_id_field = "service_id"
    context_name = "service"
    success_url_name = "dashboard:services"

    def get_instance(self, object_id):
        return editor_instance(self.model_class, object_id)

    def success_message(self, saved):
        return f"{saved.title} was saved successfully."


class DeleteServiceView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        service_id = request.POST.get("service_id")
        Service.objects.filter(id=service_id).delete()
        return redirect_back(request, "dashboard:index")


class TeamLeadsView(View):
    template_name = "dashboard/team_leads.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {"team_leads": TeamLead.objects.all().order_by("-id")}
        return render(request, self.template_name, context)


class CreateUpdateTeamLead(ContentEditorView):
    template_name = "dashboard/create_update_team_lead.html"
    form_class = TeamLeadForm
    model_class = TeamLead
    object_id_field = "team_lead_id"
    context_name = "team_lead"
    success_url_name = "dashboard:team_leads"

    def get_instance(self, object_id):
        return editor_instance(self.model_class, object_id)

    def success_message(self, saved):
        visibility = "visible" if saved.visible else "hidden"
        return f"{saved.fullname} was saved successfully and is {visibility} on the website."


class DeleteTeamLeadView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        team_lead = CreateUpdateTeamLead().get_instance(request.POST.get("team_lead_id"))
        if team_lead is None:
            raise Http404("Team lead not found.")
        team_lead.delete()
        return redirect_back(request, "dashboard:index")


class HomepageContentView(View):
    template_name = "dashboard/homepage_content.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {
            "banners": Banner.objects.select_related("service").all(),
            "shortcuts": HomepageShortcut.objects.select_related(
                "service"
            ).all(),
            "homepage_video": HomepageVideo.objects.first(),
        }
        return render(request, self.template_name, context)


class BannersView(HomepageContentView):
    """Keep the original banner URL working as a homepage CMS alias."""


class CreateUpdateBannerView(ContentEditorView):
    template_name = "dashboard/create_update_banner.html"
    form_class = BannerForm
    model_class = Banner
    object_id_field = "banner_id"
    context_name = "banner"
    success_url_name = "dashboard:homepage_content"

    @staticmethod
    def get_instance(banner_id):
        return editor_instance(Banner, banner_id)

    def success_message(self, saved):
        return f'Homepage banner "{saved.title}" was saved successfully.'


class DeleteBannerView(View):
    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        banner = CreateUpdateBannerView.get_instance(request.POST.get("banner_id"))
        if banner is None:
            raise Http404("Banner not found.")
        title = banner.title
        banner.delete()
        messages.success(
            request,
            f'Homepage banner "{title}" was removed.',
        )
        return redirect("dashboard:homepage_content")


class CreateUpdateHomepageShortcutView(ContentEditorView):
    template_name = "dashboard/create_update_homepage_shortcut.html"
    form_class = HomepageShortcutForm
    model_class = HomepageShortcut
    object_id_field = "shortcut_id"
    context_name = "shortcut"
    success_url_name = "dashboard:homepage_content"

    def success_message(self, saved):
        return f'Homepage shortcut "{saved.display_label}" was saved successfully.'


class DeleteHomepageShortcutView(View):
    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        shortcut = get_object_or_404(
            HomepageShortcut,
            id=request.POST.get("shortcut_id"),
        )
        label = shortcut.display_label
        shortcut.delete()
        messages.success(
            request,
            f'Homepage shortcut "{label}" was removed.',
        )
        return redirect("dashboard:homepage_content")


class CreateUpdateHomepageVideoView(ContentEditorView):
    template_name = "dashboard/create_update_homepage_video.html"
    form_class = HomepageVideoForm
    model_class = HomepageVideo
    object_id_field = "homepage_video_id"
    context_name = "homepage_video"
    singleton = True
    success_url_name = "dashboard:homepage_content"

    def success_message(self, saved):
        return f'Homepage video "{saved.title}" was saved successfully.'


class DeleteHomepageVideoView(View):
    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        homepage_video = get_object_or_404(
            HomepageVideo,
            id=request.POST.get("homepage_video_id"),
        )
        title = homepage_video.title
        homepage_video.delete()
        messages.success(
            request,
            f'Homepage video "{title}" was removed.',
        )
        return redirect("dashboard:homepage_content")


class ClientsView(View):
    template_name = "dashboard/clients.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {}

        return render(request, self.template_name, context)


class PostsView(View):
    template_name = "dashboard/posts.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {"posts": Post.objects.all()}
        return render(request, self.template_name, context)


class CreateUpdatePostView(ContentEditorView):
    template_name = "dashboard/create_update_post.html"
    form_class = PostForm
    model_class = Post
    object_id_field = "post_id"
    context_name = "post"
    author_field = "by"
    success_url_name = "dashboard:posts"


class DeletePostView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        post_id = request.POST.get("post_id")
        Post.objects.filter(id=post_id).delete()
        return redirect_back(request, "dashboard:index")


class AppointmentView(View):
    template_name = "dashboard/appointments.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {
            "appointments": filtered_appointments(request),
            "status_choices": Appointment.Status.choices,
            "service_choices": Appointment.objects.exclude(
                service=""
            ).order_by("service").values_list(
                "service",
                flat=True,
            ).distinct(),
            "assignable_administrators": Administrator.objects.filter(
                Q(is_superuser=True)
                | Q(role=Administrator.Role.FRONT_DESK),
                is_active=True,
                is_staff=True,
            ).order_by("fullname", "email_address"),
        }

        return render(request, self.template_name, context)


class UpdateAppointmentView(View):
    @method_decorator(staff_only())
    @transaction.atomic
    def post(self, request, appointment_id, *args, **kwargs):
        appointment = get_object_or_404(Appointment, id=appointment_id)
        requested_status = request.POST.get("status", "")
        assigned_to_id = request.POST.get("assigned_to", "")

        if requested_status not in dict(Appointment.Status.choices):
            messages.error(request, "Choose a valid appointment status.")
            return redirect_back(request, "dashboard:appointments")

        assigned_to = None
        if assigned_to_id:
            assigned_to = Administrator.objects.filter(
                Q(is_superuser=True)
                | Q(role=Administrator.Role.FRONT_DESK),
                id=assigned_to_id,
                is_active=True,
                is_staff=True,
            ).first()
            if assigned_to is None:
                messages.error(
                    request,
                    "Choose an active Front Desk administrator.",
                )
                return redirect_back(request, "dashboard:appointments")

        previous_status = appointment.status
        appointment.status = requested_status
        appointment.assigned_to = assigned_to
        appointment.internal_notes = request.POST.get(
            "internal_notes",
            "",
        ).strip()
        update_fields = [
            "status",
            "assigned_to",
            "internal_notes",
            "updated_at",
        ]

        if previous_status != appointment.status:
            appointment.status_updated_at = timezone.now()
            update_fields.append("status_updated_at")

        appointment.save(update_fields=update_fields)

        if previous_status != appointment.status:
            AppointmentStatusAudit.objects.create(
                appointment=appointment,
                changed_by=request.user,
                previous_status=previous_status,
                new_status=appointment.status,
            )

        messages.success(
            request,
            (
                f"Appointment for {appointment.fullname} was updated "
                f"successfully to {appointment.get_status_display()}."
            ),
        )
        return redirect_back(request, "dashboard:appointments")


class ExportAppointmentsView(View):
    @method_decorator(staff_only())
    def get(self, request, *args, **kwargs):
        response = HttpResponse(
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="sinel-appointments-'
            f'{timezone.localdate():%Y%m%d}.csv"'
        )
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([
            "Booked At",
            "Full Name",
            "Date of Birth",
            "Email",
            "Phone",
            "Service",
            "Preferred Date",
            "Preferred Time",
            "Status",
            "Assigned To",
            "Patient Message",
            "Internal Notes",
        ])

        appointments = list(filtered_appointments(request))
        for appointment in appointments:
            writer.writerow([
                appointment.created_at.isoformat(),
                spreadsheet_safe(appointment.fullname),
                appointment.date_of_birth or "",
                spreadsheet_safe(appointment.email),
                spreadsheet_safe(appointment.number),
                spreadsheet_safe(appointment.service),
                appointment.date,
                appointment.time,
                appointment.get_status_display(),
                spreadsheet_safe(appointment.assigned_to),
                spreadsheet_safe(appointment.message),
                spreadsheet_safe(appointment.internal_notes),
            ])

        export_filters = {
            key: request.GET.get(key, "")
            for key in (
                "q",
                "status",
                "service",
                "date_from",
                "date_to",
            )
            if request.GET.get(key)
        }
        AppointmentExportAudit.objects.create(
            exported_by=request.user,
            filters=export_filters,
            record_count=len(appointments),
        )

        return response


class TestimonialsView(View):
    template_name = "dashboard/testimonials.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        testimonials = Testimonial.objects.all()
        context = {"testimonials": testimonials}
        return render(request, self.template_name, context)


class CreateUpdateTestimonial(ContentEditorView):
    template_name = "dashboard/create_update_testimonial.html"
    form_class = TestimonialForm
    model_class = Testimonial
    object_id_field = "testimonial_id"
    context_name = "testimonial"
    author_field = "added_by"
    success_url_name = "dashboard:testimonials"


class DeleteTestimonialView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        testimonial_id = request.POST.get("testimonial_id")
        Testimonial.objects.filter(id=testimonial_id).delete()
        return redirect_back(request, "dashboard:index")


class PartnersView(View):
    template_name = "dashboard/partners.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {"partners": Partner.objects.all().order_by("-id")}
        return render(request, self.template_name, context)


class CreateUpdatePartner(ContentEditorView):
    template_name = "dashboard/create_update_partner.html"
    form_class = PartnerForm
    model_class = Partner
    object_id_field = "partner_id"
    context_name = "partner"
    success_url_name = "dashboard:partners"


class DeletePartnerView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        partner_id = request.POST.get("partner_id")
        Partner.objects.filter(id=partner_id).delete()
        return redirect_back(request, "dashboard:index")


class PagesView(View):
    template_name = "dashboard/pages.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {"pages": Page.objects.all()}
        return render(request, self.template_name, context)


class CreateUpdatePageView(ContentEditorView):
    template_name = "dashboard/create_update_page.html"
    form_class = PageForm
    model_class = Page
    object_id_field = "page_id"
    context_name = "page"
    author_field = "by"
    success_url_name = "dashboard:pages"
    derived_fields = ("slug",)


class DeletePageView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        page_id = request.POST.get("page_id")
        Page.objects.filter(id=page_id).delete()
        return redirect_back(request, "dashboard:index")


class NotificationsView(View):
    template_name = "dashboard/notifications.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {"notifications": Notification.objects.all()}
        return render(request, self.template_name, context)


class CreateUpdateNotificationView(ContentEditorView):
    template_name = "dashboard/create_update_notification.html"
    form_class = NotificationForm
    model_class = Notification
    object_id_field = "notification_id"
    context_name = "notification"
    success_url_name = "dashboard:notifications"
    derived_fields = ("content_hash",)


class DeleteNotificationView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        notification_id = request.POST.get("notification_id")
        Notification.objects.filter(id=notification_id).delete()
        return redirect_back(request, "dashboard:index")
