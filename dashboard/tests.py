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
    Banner,
    HomepageShortcut,
    HomepageVideo,
    Service,
    TeamLead,
)


PASSWORD = "Containment!Pass2026"


class BannerDashboardValidationTests(TestCase):
    def setUp(self):
        self.staff = create_user("banner-review@example.test", True)
        self.client.force_login(self.staff)
        self.banner = Banner.objects.create(
            title="Existing headline", image="uploads/images/banner.jpg", visible=True
        )

    def test_dashboard_edit_updates_copy_and_can_clear_optional_text(self):
        response = self.client.post(
            reverse("dashboard:create_update_banner"),
            {
                "banner_id": self.banner.pk,
                "title": "Edited headline\nSecond line",
                "eyebrow": "",
                "description": "",
                "button_label": "Explore our services",
                "position": 1,
                "visible": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "was saved successfully")
        self.banner.refresh_from_db()
        self.assertEqual(self.banner.title, "Edited headline\nSecond line")
        self.assertEqual(self.banner.eyebrow, "")
        self.assertFalse(self.banner.description)
        self.assertContains(
            self.client.get(reverse("website:index")), "Edited headline\nSecond line"
        )

    def test_invalid_banner_submission_preserves_copy_without_saving(self):
        response = self.client.post(
            reverse("dashboard:create_update_banner"),
            {
                "banner_id": self.banner.pk,
                "title": "Attempted headline",
                "eyebrow": "Entered heading",
                "description": "Entered supporting text",
                "button_label": "Explore our services",
                "position": 1,
                "url": "javascript:alert(1)",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Attempted headline", status_code=400)
        self.assertContains(response, "Entered supporting text", status_code=400)
        self.assertIn("url", response.context["form"].errors)
        self.banner.refresh_from_db()
        self.assertEqual(self.banner.title, "Existing headline")
        self.assertTrue(self.banner.visible)

    def test_bad_record_ids_return_not_found_and_preserve_records(self):
        for record_id in ("invalid", "-1", "9" * 100):
            for route in ("create_update_banner", "delete_banner"):
                response = self.client.post(
                    reverse(f"dashboard:{route}"), {"banner_id": record_id}
                )
                self.assertEqual(response.status_code, 404)
            response = self.client.get(
                reverse("dashboard:create_update_banner"), {"banner_id": record_id}
            )
            self.assertEqual(response.status_code, 404)
        self.assertTrue(Banner.objects.filter(pk=self.banner.pk).exists())

    def test_front_desk_cannot_mutate_banner_content(self):
        front_desk = create_user(
            "banner-frontdesk@example.test", True, role=Administrator.Role.FRONT_DESK
        )
        self.client.force_login(front_desk)
        for route in ("create_update_banner", "delete_banner"):
            response = self.client.post(
                reverse(f"dashboard:{route}"),
                {"banner_id": self.banner.pk, "title": "Not permitted"},
            )
            self.assertEqual(response.status_code, 403)
        self.banner.refresh_from_db()
        self.assertEqual(self.banner.title, "Existing headline")


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
        role=(Administrator.Role.SUPER_ADMIN if is_superuser else role),
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
        audit = AppointmentStatusAudit.objects.get(appointment=self.latest)
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

        response = self.client.get(reverse("dashboard:appointments_export"))

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
        appointment_response = self.client.get(reverse("dashboard:appointments"))

        self.assertEqual(content_response.status_code, 200)
        self.assertEqual(appointment_response.status_code, 403)

    def test_auditor_can_view_but_cannot_export_or_change_appointment(self):
        self.client.force_login(self.auditor)

        list_response = self.client.get(reverse("dashboard:appointments"))
        export_response = self.client.get(reverse("dashboard:appointments_export"))
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

        list_response = self.client.get(reverse("dashboard:homepage_content"))
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
            HomepageShortcut.objects.filter(label="Unauthorized shortcut").exists()
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
            Award.objects.filter(title="Unauthorized recognition").exists()
        )


class TeamLeadVisibilityTests(TestCase):
    def setUp(self):
        self.content_manager = create_user(
            "team-content-manager@example.test",
            True,
        )
        self.visible_member = TeamLead.objects.create(
            fullname="Dr Visible Member",
            title="General Medicine",
            bio="An experienced member of our clinical team.",
            photo="uploads/images/visible-member.jpg",
            visible=True,
        )
        self.hidden_member = TeamLead.objects.create(
            fullname="Dr Hidden Member",
            title="General Medicine",
            bio="A profile that is not displayed publicly.",
            photo="uploads/images/hidden-member.jpg",
            visible=False,
        )
        self.service = Service.objects.create(
            title="Team Visibility Care",
            description="<p>Meet our clinical team.</p>",
            schedules="<p>Every day</p>",
            image="uploads/images/team-visibility.jpg",
            visible=True,
        )
        self.service.doctors.add(self.visible_member, self.hidden_member)
        self.client.force_login(self.content_manager)

    def member_data(self, member, visible=False):
        data = {
            "team_lead_id": member.pk,
            "fullname": member.fullname,
            "title": member.title,
            "bio": member.bio,
            "linkedin": "",
        }
        if visible:
            data["visible"] = "on"
        return data

    def test_list_and_edit_form_use_the_same_visibility(self):
        response = self.client.get(reverse("dashboard:team_leads"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Website visibility")
        self.assertContains(
            response,
            '<span class="badge badge-success">Visible</span>',
            count=1,
        )
        self.assertContains(
            response,
            '<span class="badge badge-secondary">Hidden</span>',
            count=1,
        )
        self.assertNotContains(response, "Inactive")

        for member in (self.visible_member, self.hidden_member):
            with self.subTest(visible=member.visible):
                edit_response = self.client.get(
                    reverse("dashboard:create_update_team_lead"),
                    {"team_lead_id": member.pk},
                )
                self.assertEqual(edit_response.status_code, 200)
                self.assertEqual(
                    edit_response.context["form"]["visible"].value(),
                    member.visible,
                )
                checked_toggle = 'name="visible" id="visible" checked'
                if member.visible:
                    self.assertContains(edit_response, checked_toggle)
                else:
                    self.assertNotContains(edit_response, checked_toggle)
                self.assertNotContains(
                    edit_response,
                    "can access this dashboard",
                )

    def test_unchecked_toggle_hides_member_from_all_public_team_views(self):
        response = self.client.post(
            reverse("dashboard:create_update_team_lead"),
            self.member_data(self.visible_member),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.visible_member.refresh_from_db()
        self.assertFalse(self.visible_member.visible)
        self.assertContains(
            response,
            "was saved successfully and is hidden on the website",
        )
        self.assertContains(
            response,
            '<span class="badge badge-secondary">Hidden</span>',
            count=2,
        )

        team_response = self.client.get(reverse("website:doctors"))
        self.assertEqual(list(team_response.context["doctors"]), [])
        self.assertEqual(list(team_response.context["hero_members"]), [])
        self.assertNotContains(team_response, self.visible_member.fullname)

        homepage_response = self.client.get(reverse("website:index"))
        self.assertEqual(list(homepage_response.context["team"]), [])
        self.assertNotContains(homepage_response, self.visible_member.fullname)

        service_response = self.client.get(
            reverse("website:service_details", args=[self.service.pk]),
        )
        self.assertEqual(list(service_response.context["doctors"]), [])
        self.assertNotContains(service_response, self.visible_member.fullname)

    def test_checked_toggle_makes_hidden_member_public(self):
        response = self.client.post(
            reverse("dashboard:create_update_team_lead"),
            self.member_data(self.hidden_member, visible=True),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.hidden_member.refresh_from_db()
        self.assertTrue(self.hidden_member.visible)
        self.assertContains(
            response,
            "was saved successfully and is visible on the website",
        )
        team_response = self.client.get(reverse("website:doctors"))
        self.assertIn(self.hidden_member, team_response.context["doctors"])
        self.assertContains(team_response, self.hidden_member.fullname)

    def test_invalid_update_preserves_values_and_checkbox_without_saving(self):
        data = self.member_data(self.visible_member)
        data["fullname"] = "Dr Revised Member"
        data["bio"] = "Updated biography awaiting a correction."
        data["linkedin"] = "not-a-valid-url"

        response = self.client.post(
            reverse("dashboard:create_update_team_lead"),
            data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Dr Revised Member"')
        self.assertContains(response, data["bio"])
        self.assertContains(response, 'value="not-a-valid-url"')
        self.assertContains(response, "Enter a valid URL.")
        self.assertFalse(response.context["form"]["visible"].value())
        self.assertNotContains(response, 'name="visible" id="visible" checked')
        self.visible_member.refresh_from_db()
        self.assertEqual(self.visible_member.fullname, "Dr Visible Member")
        self.assertTrue(self.visible_member.visible)

    def test_invalid_new_member_shows_photo_error_and_keeps_visible_choice(self):
        response = self.client.post(
            reverse("dashboard:create_update_team_lead"),
            {
                "fullname": "Dr New Member",
                "title": "General Medicine",
                "bio": "A new clinical team profile.",
                "visible": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("photo", response.context["form"].errors)
        self.assertContains(response, 'value="Dr New Member"')
        self.assertContains(response, 'name="visible" id="visible" checked')
        self.assertFalse(TeamLead.objects.filter(fullname="Dr New Member").exists())

    def test_invalid_or_missing_member_id_returns_not_found(self):
        for member_id in (999999, "invalid"):
            with self.subTest(member_id=member_id):
                url = reverse("dashboard:create_update_team_lead")
                self.assertEqual(
                    self.client.get(url, {"team_lead_id": member_id}).status_code,
                    404,
                )
                data = self.member_data(self.visible_member)
                data["team_lead_id"] = member_id
                self.assertEqual(self.client.post(url, data).status_code, 404)

    def test_front_desk_cannot_change_team_visibility(self):
        front_desk = create_user(
            "team-front-desk@example.test",
            True,
            role=Administrator.Role.FRONT_DESK,
        )
        self.client.force_login(front_desk)

        response = self.client.post(
            reverse("dashboard:create_update_team_lead"),
            self.member_data(self.visible_member),
        )

        self.assertEqual(response.status_code, 403)
        self.visible_member.refresh_from_db()
        self.assertTrue(self.visible_member.visible)
