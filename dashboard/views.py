import csv

from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse
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
    AboutMissionForm,
    AboutOverviewForm,
    AboutValueForm,
    AboutVisionForm,
    AwardForm,
    BannerForm,
    HomepageShortcutForm,
    HomepageVideoForm,
    MediaForm,
    NotificationForm,
    PartnerForm,
    ServiceForm,
    TeamLeadForm,
    TestimonialForm,
)
from django.utils.html import strip_tags
from django.utils import timezone
from django.utils.dateparse import parse_date
from accounts.models import Administrator


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
        "overview": AboutOverviewForm,
        "mission": AboutMissionForm,
        "vision": AboutVisionForm,
        "value": AboutValueForm,
    }

    def get_context(self, about, bound_form=None, section=None):
        section_forms = {
            name: (
                bound_form
                if name == section and bound_form is not None
                else form_class(instance=about)
            )
            for name, form_class in self.form_classes.items()
        }
        editor_media = section_forms["overview"].media
        for name in ("mission", "vision", "value"):
            editor_media += section_forms[name].media
        return {
            "about": about,
            "overview_form": section_forms["overview"],
            "mission_form": section_forms["mission"],
            "vision_form": section_forms["vision"],
            "value_form": section_forms["value"],
            "editor_media": editor_media,
            "active_section": section or "overview",
        }

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        about = get_object_or_404(About, pk=About.objects.values_list("pk", flat=True).first())
        return render(request, self.template_name, self.get_context(about))

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        section = request.POST.get("section", "")
        form_class = self.form_classes.get(section)
        if form_class is None:
            messages.error(request, "Choose a valid About section.")
            return redirect("dashboard:about")

        about = get_object_or_404(About, pk=About.objects.values_list("pk", flat=True).first())
        form = form_class(request.POST, instance=about)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self.get_context(about, bound_form=form, section=section),
                status=400,
            )

        form.save()
        messages.success(request, f"{section.title()} updated.")
        return redirect_back(request, "dashboard:index")


class AwardsView(View):
    template_name = "dashboard/awards.html"

    @method_decorator(staff_only())
    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.template_name,
            {"awards": Award.objects.all()},
        )


class CreateUpdateAwardView(View):
    template_name = "dashboard/create_update_award.html"

    @method_decorator(staff_only())
    def get(self, request, *args, **kwargs):
        award_id = request.GET.get("award_id")
        award = (
            get_object_or_404(Award, id=award_id)
            if award_id
            else None
        )
        return render(
            request,
            self.template_name,
            {
                "award": award,
                "form": AwardForm(instance=award),
            },
        )

    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        award_id = request.POST.get("award_id")
        award = (
            get_object_or_404(Award, id=award_id)
            if award_id
            else None
        )
        form = AwardForm(
            request.POST,
            request.FILES or None,
            instance=award,
        )
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"award": award, "form": form},
                status=400,
            )

        saved_award = form.save()
        messages.success(
            request,
            f'Award "{saved_award.title}" was saved successfully.',
        )
        return redirect("dashboard:awards")


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


class ContactView(View):
    template_name = "dashboard/contact.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        context = {"contact": Contact.objects.first()}
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        email = request.POST.get("email")
        gps = request.POST.get("gps")
        address = request.POST.get("address")
        telephone = request.POST.get("telephone")
        lat_lng = request.POST.get("lat_lng")

        contact = Contact.objects.first()

        if email:
            contact.email = email
        if gps:
            contact.gps = gps
        if address:
            contact.address = address
        if telephone:
            contact.telephone = telephone
        if lat_lng:
            contact.lat_lng = lat_lng
        contact.save()
        return redirect_back(request, "dashboard:index")


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


class CreateUpdateAlbum(View):
    template_name = "dashboard/create_update_album.html"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        album_id = request.GET.get("album_id", -1)
        context = {"album": Album.objects.filter(id=album_id).first()}
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        album_id = request.POST.get("album_id") or None
        name = request.POST.get("name")
        service = Album.objects.filter(id=album_id).first()
        if service:
            # Update
            service.name = name
            service.save()
        else:
            Album.objects.create(name=name)
        return redirect("dashboard:gallery")


class DeleteAlbumView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        album_id = request.POST.get("album_id")
        Album.objects.filter(id=album_id).delete()
        return redirect_back(request, "dashboard:index")


class CreateUpdateMedia(View):
    template_name = "dashboard/create_update_media.html"
    form_class = MediaForm
    model_class = Media
    object_id_field = "media_id"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        media_id = request.GET.get("media_id", -1) or None
        context = {
            "albums": Album.objects.all(),
            "media": Media.objects.filter(id=media_id).first(),
        }
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        object_id = request.POST.get(self.object_id_field) or None
        instance = None
        if object_id:
            instance = get_object_or_404(self.model_class, id=object_id)
        form = self.form_class(request.POST,
                               request.FILES or None,
                               instance=instance)
        if form.is_valid():
            media = form.save()
        else:
            for field, er in form.errors.items():
                message = f"{field.title()}: {strip_tags(er)}"
                messages.add_message(request, messages.ERROR, message)
            return redirect_back(request, "dashboard:index")
        return redirect(to="dashboard:album", album_id=media.album.id)


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


class CreateUpdateService(View):
    template_name = "dashboard/create_update_service.html"
    form_class = ServiceForm
    model_class = Service
    object_id_field = "service_id"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        service_id = request.GET.get("service_id", -1)
        service = Service.objects.filter(id=service_id).first()
        form = self.form_class(instance=service)
        context = {
            "service": service,
            "form": form,
            "doctors": TeamLead.objects.filter(visible=True),
        }
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        object_id = request.POST.get(self.object_id_field) or None
        instance = None
        if object_id:
            instance = get_object_or_404(self.model_class, id=object_id)
        form = self.form_class(request.POST,
                               request.FILES or None,
                               instance=instance)
        if form.is_valid():
            form.save()
        else:
            for field, er in form.errors.items():
                message = f"{field.title()}: {strip_tags(er)}"
                messages.add_message(request, messages.ERROR, message)
            return redirect_back(request, "dashboard:index")
        return redirect("dashboard:services")


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


class CreateUpdateTeamLead(View):
    template_name = "dashboard/create_update_team_lead.html"
    form_class = TeamLeadForm
    model_class = TeamLead
    object_id_field = "team_lead_id"

    def get_instance(self, object_id):
        if not object_id:
            return None
        try:
            object_id = int(object_id)
        except (TypeError, ValueError):
            raise Http404("Team lead not found.")
        if not 1 <= object_id <= 9223372036854775807:
            raise Http404("Team lead not found.")
        return get_object_or_404(self.model_class, id=object_id)

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        instance = self.get_instance(request.GET.get(self.object_id_field))
        context = {
            "team_lead": instance,
            "form": self.form_class(instance=instance),
        }
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        instance = self.get_instance(request.POST.get(self.object_id_field))
        form = self.form_class(request.POST,
                               request.FILES or None,
                               instance=instance)
        if form.is_valid():
            team_lead = form.save()
            visibility = "visible" if team_lead.visible else "hidden"
            messages.success(
                request,
                f"{team_lead.fullname} was saved successfully and is {visibility} on the website.",
            )
            return redirect("dashboard:team_leads")
        return render(
            request,
            self.template_name,
            {"team_lead": instance, "form": form},
        )


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


class CreateUpdateBannerView(View):
    template_name = "dashboard/create_update_banner.html"

    @staticmethod
    def get_instance(banner_id):
        if not banner_id:
            return None
        try:
            banner_id = int(banner_id)
        except (ValueError, TypeError):
            raise Http404("Banner not found.")
        if not 1 <= banner_id <= 9223372036854775807:
            raise Http404("Banner not found.")
        return get_object_or_404(Banner, id=banner_id)

    @method_decorator(staff_only())
    def get(self, request, *args, **kwargs):
        banner_id = request.GET.get("banner_id")
        banner = self.get_instance(banner_id)
        return render(
            request,
            self.template_name,
            {
                "banner": banner,
                "form": BannerForm(instance=banner),
            },
        )

    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        banner_id = request.POST.get("banner_id")
        banner = self.get_instance(banner_id)
        form = BannerForm(
            request.POST,
            request.FILES or None,
            instance=banner,
        )
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"banner": banner, "form": form},
                status=400,
            )

        saved_banner = form.save()
        messages.success(
            request,
            f'Homepage banner "{saved_banner.title}" was saved successfully.',
        )
        return redirect("dashboard:homepage_content")


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


class CreateUpdateHomepageShortcutView(View):
    template_name = "dashboard/create_update_homepage_shortcut.html"

    @method_decorator(staff_only())
    def get(self, request, *args, **kwargs):
        shortcut_id = request.GET.get("shortcut_id")
        shortcut = (
            get_object_or_404(HomepageShortcut, id=shortcut_id)
            if shortcut_id
            else None
        )
        return render(
            request,
            self.template_name,
            {
                "shortcut": shortcut,
                "form": HomepageShortcutForm(instance=shortcut),
            },
        )

    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        shortcut_id = request.POST.get("shortcut_id")
        shortcut = (
            get_object_or_404(HomepageShortcut, id=shortcut_id)
            if shortcut_id
            else None
        )
        form = HomepageShortcutForm(request.POST, instance=shortcut)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"shortcut": shortcut, "form": form},
                status=400,
            )

        saved_shortcut = form.save()
        messages.success(
            request,
            (
                f'Homepage shortcut "{saved_shortcut.display_label}" '
                "was saved successfully."
            ),
        )
        return redirect("dashboard:homepage_content")


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


class CreateUpdateHomepageVideoView(View):
    template_name = "dashboard/create_update_homepage_video.html"

    @method_decorator(staff_only())
    def get(self, request, *args, **kwargs):
        homepage_video = HomepageVideo.objects.first()
        return render(
            request,
            self.template_name,
            {
                "homepage_video": homepage_video,
                "form": HomepageVideoForm(instance=homepage_video),
            },
        )

    @method_decorator(staff_only())
    def post(self, request, *args, **kwargs):
        homepage_video = HomepageVideo.objects.first()
        form = HomepageVideoForm(
            request.POST,
            request.FILES or None,
            instance=homepage_video,
        )
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "homepage_video": homepage_video,
                    "form": form,
                },
                status=400,
            )

        saved_video = form.save()
        messages.success(
            request,
            f'Homepage video "{saved_video.title}" was saved successfully.',
        )
        return redirect("dashboard:homepage_content")


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


class CreateUpdatePostView(View):
    template_name = "dashboard/create_update_post.html"
    form_class = PostForm
    model_class = Post
    object_id_field = "post_id"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        post_id = request.GET.get("post_id", -1)
        post = self.model_class.objects.filter(id=post_id).first()
        context = {
            "post": post,
            "form": self.form_class(instance=post),
        }
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        object_id = request.POST.get(self.object_id_field) or None
        instance = None
        if object_id:
            instance = get_object_or_404(self.model_class, id=object_id)
        form = self.form_class(request.POST,
                               request.FILES or None,
                               instance=instance)
        if form.is_valid():
            post = form.save(commit=False)
            post.by = request.user
            post.save()
        else:
            for field, er in form.errors.items():
                message = f"{field.title()}: {strip_tags(er)}"
                messages.add_message(request, messages.ERROR, message)
            return redirect_back(request, "dashboard:index")
        return redirect("dashboard:posts")


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


class CreateUpdateTestimonial(View):
    template_name = "dashboard/create_update_testimonial.html"
    form_class = TestimonialForm
    model_class = Testimonial
    object_id_field = "testimonial_id"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        testimonial_id = request.GET.get("testimonial_id", -1)
        context = {
            "services": Service.objects.filter(visible=True),
            "doctors": TeamLead.objects.filter(visible=True),
            "testimonial":
            Testimonial.objects.filter(id=testimonial_id).first()
        }
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        object_id = request.POST.get(self.object_id_field) or None
        instance = None
        if object_id:
            instance = get_object_or_404(self.model_class, id=object_id)
        form = self.form_class(request.POST,
                               request.FILES or None,
                               instance=instance)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.added_by = request.user
            testimonial.save()
        else:
            for field, er in form.errors.items():
                message = f"{field.title()}: {strip_tags(er)}"
                messages.add_message(request, messages.ERROR, message)
            return redirect_back(request, "dashboard:index")
        return redirect("dashboard:testimonials")


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


class CreateUpdatePartner(View):
    template_name = "dashboard/create_update_partner.html"
    form_class = PartnerForm
    model_class = Partner
    object_id_field = "partner_id"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        partner_id = request.GET.get("partner_id", -1)
        context = {"partner": Partner.objects.filter(id=partner_id).first()}
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        object_id = request.POST.get(self.object_id_field) or None
        instance = None
        if object_id:
            instance = get_object_or_404(self.model_class, id=object_id)
        form = self.form_class(request.POST,
                               request.FILES or None,
                               instance=instance)
        if form.is_valid():
            form.save()
        else:
            for field, er in form.errors.items():
                message = f"{field.title()}: {strip_tags(er)}"
                messages.add_message(request, messages.ERROR, message)
            return redirect_back(request, "dashboard:index")
        return redirect("dashboard:partners")


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


class CreateUpdatePageView(View):
    template_name = "dashboard/create_update_page.html"
    form_class = PageForm
    model_class = Page
    object_id_field = "page_id"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        page_id = request.GET.get("page_id", -1)
        page = self.model_class.objects.filter(id=page_id).first()
        context = {
            "page": page,
            "form": self.form_class(instance=page),
        }
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        object_id = request.POST.get(self.object_id_field) or None
        instance = None
        if object_id:
            instance = get_object_or_404(self.model_class, id=object_id)
        form = self.form_class(request.POST,
                               request.FILES or None,
                               instance=instance)
        if form.is_valid():
            page = form.save(commit=False)
            page.by = request.user
            page.save()
        else:
            for field, er in form.errors.items():
                message = f"{field.title()}: {strip_tags(er)}"
                messages.add_message(request, messages.ERROR, message)
            return redirect_back(request, "dashboard:index")
        return redirect("dashboard:pages")


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


class CreateUpdateNotificationView(View):
    template_name = "dashboard/create_update_notification.html"
    form_class = NotificationForm
    model_class = Notification
    object_id_field = "notification_id"

    @method_decorator(staff_only())
    def get(self, request, *argd, **kwargs):
        notification_id = request.GET.get("notification_id", -1)
        context = {
            "notification":
            self.model_class.objects.filter(id=notification_id).first()
        }
        return render(request, self.template_name, context)

    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        object_id = request.POST.get(self.object_id_field) or None
        instance = None
        if object_id:
            instance = get_object_or_404(self.model_class, id=object_id)
        form = self.form_class(request.POST, instance=instance)
        if form.is_valid():
            form.save()
        else:
            for field, er in form.errors.items():
                message = f"{field.title()}: {strip_tags(er)}"
                messages.add_message(request, messages.ERROR, message)
            return redirect_back(request, "dashboard:index")
        return redirect("dashboard:notifications")


class DeleteNotificationView(View):
    @method_decorator(staff_only())
    def post(self, request, *argd, **kwargs):
        notification_id = request.POST.get("notification_id")
        Notification.objects.filter(id=notification_id).delete()
        return redirect_back(request, "dashboard:index")
