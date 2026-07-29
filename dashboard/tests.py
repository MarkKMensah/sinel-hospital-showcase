from django.test import TestCase
from django.urls import reverse

from accounts.models import Administrator
from communications.models import (
    Appointment,
    AppointmentExportAudit,
    AppointmentStatusAudit,
)
from website.models import (
    About,
    Award,
    HomepageShortcut,
    HomepageVideo,
    Service,
)


PASSWORD = "Containment!Pass2026"


def create_user(
    email,
    is_staff,
    role=Administrator.Role.CONTENT_MANAGER,
    is_superuser=False,
):
    return Administrator.objects.create_user(
        email_address=email,
        password=PASSWORD,
        fullname=email.split("@")[0].title(),
        title="Administrator",
        is_active=True,
        is_staff=is_staff,
        is_superuser=is_superuser,
        role=(
            Administrator.Role.SUPER_ADMIN
            if is_superuser
            else role
        ),
    )


class DashboardAccessContainmentTests(TestCase):
    def setUp(self):
        self.staff = create_user(
            "dashboard-staff@example.test",
            True,
            role=Administrator.Role.FRONT_DESK,
        )
        self.regular_user = create_user(
            "dashboard-regular@example.test",
            False,
        )
        self.first = self.create_appointment("First")
        self.latest = self.create_appointment("Latest")

    @staticmethod
    def create_appointment(fullname):
        return Appointment.objects.create(
            fullname=fullname,
            email=f"{fullname.lower()}@example.test",
            number="+233200000000",
            date="2026-08-01",
            time="09:00",
            date_of_birth="1990-01-01",
            message="Containment test appointment.",
            service="General consultation",
        )

    def test_anonymous_user_cannot_view_appointments(self):
        response = self.client.get(reverse("dashboard:appointments"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("accounts:login")))

    def test_authenticated_non_staff_user_gets_forbidden(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("dashboard:appointments"))

        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_view_latest_appointment_first(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:appointments"))

        self.assertEqual(response.status_code, 200)
        appointments = list(response.context["appointments"])
        self.assertEqual(
            [appointment.pk for appointment in appointments],
            [self.latest.pk, self.first.pk],
        )

    def test_front_desk_can_filter_appointments_by_status(self):
        self.first.status = Appointment.Status.COMPLETED
        self.first.save(update_fields=["status"])
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("dashboard:appointments"),
            {"status": Appointment.Status.NEW},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["appointments"]),
            [self.latest],
        )

    def test_front_desk_can_update_status_with_audit_and_notice(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse(
                "dashboard:appointment_update",
                args=[self.latest.pk],
            ),
            {
                "status": Appointment.Status.CONTACTED,
                "assigned_to": self.staff.pk,
                "internal_notes": "Called patient; awaiting confirmation.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.latest.refresh_from_db()
        self.assertEqual(self.latest.status, Appointment.Status.CONTACTED)
        self.assertEqual(self.latest.assigned_to, self.staff)
        self.assertContains(response, "was updated successfully")
        audit = AppointmentStatusAudit.objects.get(
            appointment=self.latest
        )
        self.assertEqual(audit.changed_by, self.staff)
        self.assertEqual(audit.previous_status, Appointment.Status.NEW)
        self.assertEqual(audit.new_status, Appointment.Status.CONTACTED)

    def test_front_desk_can_export_filtered_csv(self):
        self.first.status = Appointment.Status.COMPLETED
        self.first.save(update_fields=["status"])
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("dashboard:appointments_export"),
            {"status": Appointment.Status.NEW},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "text/csv; charset=utf-8",
        )
        exported = response.content.decode("utf-8-sig")
        self.assertIn("Latest", exported)
        self.assertNotIn("First", exported)
        export_audit = AppointmentExportAudit.objects.get()
        self.assertEqual(export_audit.exported_by, self.staff)
        self.assertEqual(export_audit.record_count, 1)
        self.assertEqual(
            export_audit.filters,
            {"status": Appointment.Status.NEW},
        )

    def test_export_prevents_spreadsheet_formula_execution(self):
        self.latest.fullname = "=2+2"
        self.latest.save(update_fields=["fullname"])
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("dashboard:appointments_export")
        )

        exported = response.content.decode("utf-8-sig")
        self.assertIn("'=2+2", exported)

    def test_front_desk_cannot_access_content_management(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:services"))

        self.assertEqual(response.status_code, 403)

    def test_authenticated_non_staff_user_cannot_view_dashboard(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 403)


class EditorModernizationTests(TestCase):
    def setUp(self):
        self.staff = create_user("editor-staff@example.test", True)
        self.regular_user = create_user(
            "editor-regular@example.test",
            False,
        )
        self.about = About.objects.create(
            overview="<p>Overview</p>",
            mission="<p>Mission</p>",
            vision="<p>Vision</p>",
            value="<p>Value</p>",
        )

    def test_about_editor_uses_ckeditor_5_assets_once(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "/static/django_ckeditor_5/dist/bundle.js",
            count=1,
        )
        self.assertNotContains(response, "cdn.ckeditor.com/4.")
        self.assertNotContains(response, "CKEDITOR.replace")

    def test_about_editor_updates_only_selected_section(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:about"),
            {
                "section": "overview",
                "overview": "<h2>Updated overview</h2>",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.about.refresh_from_db()
        self.assertEqual(self.about.overview, "<h2>Updated overview</h2>")
        self.assertEqual(self.about.mission, "<p>Mission</p>")

    def test_non_staff_user_cannot_upload_editor_files(self):
        self.client.force_login(self.regular_user)

        response = self.client.post(reverse("ck_editor_5_upload_file"))

        self.assertEqual(response.status_code, 403)


class DashboardRoleAccessTests(TestCase):
    def setUp(self):
        self.content_manager = create_user(
            "content-manager@example.test",
            True,
            role=Administrator.Role.CONTENT_MANAGER,
        )
        self.auditor = create_user(
            "auditor@example.test",
            True,
            role=Administrator.Role.AUDITOR,
        )
        self.appointment = Appointment.objects.create(
            fullname="Role Test",
            email="role@example.test",
            number="+233200000001",
            date="2026-08-01",
            time="10:00",
            message="Role access test.",
            service="General consultation",
        )
        self.service = Service.objects.create(
            title="Primary Care",
            description="<p>Care for everyday health needs.</p>",
            schedules="<p>Every day</p>",
            image="uploads/images/primary-care.jpg",
            visible=True,
        )

    def test_content_manager_can_manage_content_but_not_appointments(self):
        self.client.force_login(self.content_manager)

        content_response = self.client.get(reverse("dashboard:services"))
        appointment_response = self.client.get(
            reverse("dashboard:appointments")
        )

        self.assertEqual(content_response.status_code, 200)
        self.assertEqual(appointment_response.status_code, 403)

    def test_auditor_can_view_but_cannot_export_or_change_appointment(self):
        self.client.force_login(self.auditor)

        list_response = self.client.get(reverse("dashboard:appointments"))
        export_response = self.client.get(
            reverse("dashboard:appointments_export")
        )
        update_response = self.client.post(
            reverse(
                "dashboard:appointment_update",
                args=[self.appointment.pk],
            ),
            {"status": Appointment.Status.CONTACTED},
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(export_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)

    def test_auditor_cannot_submit_content_changes(self):
        self.client.force_login(self.auditor)

        response = self.client.post(
            reverse("dashboard:about"),
            {
                "section": "overview",
                "overview": "<p>Unauthorized change</p>",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_content_manager_can_create_homepage_shortcut_with_notice(self):
        self.client.force_login(self.content_manager)

        response = self.client.post(
            reverse("dashboard:create_update_homepage_shortcut"),
            {
                "service": self.service.pk,
                "label": "General Medicine",
                "description": "Everyday care for the whole family.",
                "icon": HomepageShortcut.Icon.PRIMARY_CARE,
                "accent": HomepageShortcut.Accent.SKY,
                "ribbon_text": "Featured",
                "ribbon_style": HomepageShortcut.RibbonStyle.NAVY,
                "ribbon_position": HomepageShortcut.RibbonPosition.RIGHT,
                "position": 10,
                "visible": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        shortcut = HomepageShortcut.objects.get()
        self.assertEqual(shortcut.service, self.service)
        self.assertEqual(shortcut.label, "General Medicine")
        self.assertEqual(shortcut.ribbon_text, "Featured")
        self.assertContains(response, "was saved successfully")

    def test_content_manager_can_manage_about_page_recognition(self):
        Award.objects.all().delete()
        self.client.force_login(self.content_manager)

        response = self.client.post(
            reverse("dashboard:create_update_award"),
            {
                "title": "Healthcare Excellence Recognition",
                "issuer": "Healthcare Council",
                "year": 2026,
                "description": "Recognition for dependable patient care.",
                "image_url": "https://example.com/award.jpg",
                "position": 10,
                "visible": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        award = Award.objects.get()
        self.assertEqual(
            award.title,
            "Healthcare Excellence Recognition",
        )
        self.assertTrue(award.visible)
        self.assertContains(response, "was saved successfully")

        delete_response = self.client.post(
            reverse("dashboard:delete_award"),
            {"award_id": award.pk},
            follow=True,
        )

        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Award.objects.exists())
        self.assertContains(delete_response, "was removed")

    def test_content_manager_can_manage_homepage_video(self):
        HomepageVideo.objects.all().delete()
        self.client.force_login(self.content_manager)

        response = self.client.post(
            reverse("dashboard:create_update_homepage_video"),
            {
                "eyebrow": "Inside Sinel",
                "title": "The New Sinel",
                "description": "A short hospital tour.",
                "youtube_url": "https://youtu.be/ZBcjm8dh1T4",
                "poster_url": "https://example.com/poster.jpg",
                "visible": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        video = HomepageVideo.objects.get()
        self.assertEqual(video.youtube_id, "ZBcjm8dh1T4")
        self.assertContains(response, "was saved successfully")

    def test_auditor_can_view_but_cannot_change_homepage_content(self):
        self.client.force_login(self.auditor)

        list_response = self.client.get(
            reverse("dashboard:homepage_content")
        )
        create_response = self.client.post(
            reverse("dashboard:create_update_homepage_shortcut"),
            {
                "service": self.service.pk,
                "label": "Unauthorized shortcut",
                "icon": HomepageShortcut.Icon.PRIMARY_CARE,
                "accent": HomepageShortcut.Accent.SKY,
                "position": 10,
                "visible": "on",
            },
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(create_response.status_code, 403)
        self.assertFalse(
            HomepageShortcut.objects.filter(
                label="Unauthorized shortcut"
            ).exists()
        )

        award_response = self.client.post(
            reverse("dashboard:create_update_award"),
            {
                "title": "Unauthorized recognition",
                "image_url": "https://example.com/award.jpg",
                "position": 10,
                "visible": "on",
            },
        )

        self.assertEqual(award_response.status_code, 403)
        self.assertFalse(
            Award.objects.filter(
                title="Unauthorized recognition"
            ).exists()
        )
