from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import Administrator
from website.forms import ServiceForm
from website.models import Service, TeamLead


class ServiceTeamLeadAssignmentFixtures:
    def setUp(self):
        media_directory = TemporaryDirectory()
        self.addCleanup(media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.manager = self.user("manager", Administrator.Role.CONTENT_MANAGER)
        self.client.force_login(self.manager)
        self.url = reverse("dashboard:create_update_service")
        self.visible_lead = self.lead("Dr Visible", visible=True)
        self.hidden_lead = self.lead("Dr Hidden", visible=False)
        self.other_hidden_lead = self.lead("Dr Other Hidden", visible=False)
        self.service = Service.objects.create(
            title="Existing service",
            description="<p>Existing service details.</p>",
            schedules="<p>Daily</p>",
            image="uploads/images/existing-service.png",
            visible=True,
        )
        self.service.doctors.set([self.visible_lead, self.hidden_lead])

    @staticmethod
    def user(name, role, *, is_staff=True, is_active=True, is_superuser=False):
        return Administrator.objects.create_user(
            email_address=f"service-{name}@example.test",
            password=None,
            fullname=name,
            title="Administrator",
            role=role,
            is_staff=is_staff,
            is_active=is_active,
            is_superuser=is_superuser,
        )

    @staticmethod
    def lead(name, *, visible):
        return TeamLead.objects.create(
            fullname=name,
            bio="An experienced team member.",
            title="Clinical specialist",
            photo="uploads/images/team-member.png",
            visible=visible,
        )

    @staticmethod
    def upload():
        buffer = BytesIO()
        Image.new("RGB", (16, 16), "blue").save(buffer, format="PNG")
        return SimpleUploadedFile(
            "service.png", buffer.getvalue(), content_type="image/png"
        )

    def payload(self, *, doctors=None, create=False):
        data = {
            "title": "Updated service" if not create else "New service",
            "description": "<p>Updated service details.</p>",
            "schedules": "<p>Monday to Friday</p>",
            "visible": "on",
        }
        if create:
            data["image"] = self.upload()
        else:
            data["service_id"] = self.service.pk
        if doctors is not None:
            data["doctors"] = doctors
        return data

    def assert_original_service(self):
        self.service.refresh_from_db()
        self.assertEqual(self.service.title, "Existing service")
        self.assertEqual(self.service.description, "<p>Existing service details.</p>")
        self.assertEqual(self.service.schedules, "<p>Daily</p>")
        self.assertEqual(self.service.image.name, "uploads/images/existing-service.png")
        self.assertTrue(self.service.visible)
        self.assertCountEqual(
            self.service.doctors.all(), [self.visible_lead, self.hidden_lead]
        )


@override_settings(SECURE_SSL_REDIRECT=False)
class ServiceTeamLeadAssignmentTests(ServiceTeamLeadAssignmentFixtures, TestCase):
    def test_model_and_dashboard_field_are_optional_multiple_team_lead(self):
        self.assertTrue(Service._meta.get_field("doctors").blank)
        response = self.client.get(self.url)
        field = response.context["form"].fields["doctors"]
        self.assertEqual(field.label, "Team Lead")
        self.assertFalse(field.required)
        self.assertContains(response, "<h4>Team Lead</h4>", html=True)
        self.assertNotContains(response, "<h4>Doctors</h4>", html=True)
        self.assertIn("multiple", str(response.context["form"]["doctors"]))
        self.assertNotIn("required", str(response.context["form"]["doctors"]))
        self.assertCountEqual(field.queryset, [self.visible_lead])

    def test_create_without_team_leads_and_without_any_available_leads(self):
        self.visible_lead.visible = False
        self.visible_lead.save(update_fields=["visible"])
        response = self.client.post(self.url, self.payload(create=True), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New service was saved successfully.")
        service = Service.objects.get(title="New service")
        self.assertFalse(service.doctors.exists())
        self.assertTrue(service.visible)

    def test_create_with_multiple_visible_team_leads(self):
        second_lead = self.lead("Dr Second Visible", visible=True)
        response = self.client.post(
            self.url,
            self.payload(doctors=[self.visible_lead.pk, second_lead.pk], create=True),
        )
        self.assertRedirects(response, reverse("dashboard:services"))
        service = Service.objects.get(title="New service")
        self.assertCountEqual(service.doctors.all(), [self.visible_lead, second_lead])

    def test_missing_or_empty_selection_clears_all_existing_assignments(self):
        for selection in (None, []):
            with self.subTest(selection=selection):
                self.service.doctors.set([self.visible_lead, self.hidden_lead])
                response = self.client.post(self.url, self.payload(doctors=selection))
                self.assertRedirects(response, reverse("dashboard:services"))
                self.assertFalse(self.service.doctors.exists())
                public = self.client.get(
                    reverse("website:service_details", args=[self.service.pk])
                )
                self.assertEqual(public.status_code, 200)
                self.assertEqual(list(public.context["doctors"]), [])
                self.assertNotContains(public, "Specialists for this service")

    def test_edit_includes_and_preselects_hidden_existing_assignments_only(self):
        response = self.client.get(self.url, {"service_id": self.service.pk})
        form = response.context["form"]
        self.assertCountEqual(
            form.fields["doctors"].queryset, [self.visible_lead, self.hidden_lead]
        )
        self.assertCountEqual(form["doctors"].value(), [self.visible_lead.pk, self.hidden_lead.pk])
        self.assertContains(response, "Dr Hidden (hidden)")
        self.assertNotContains(response, self.other_hidden_lead.fullname)

    def test_unrelated_edit_preserves_hidden_association_and_original_image(self):
        response = self.client.post(
            self.url, self.payload(doctors=[self.visible_lead.pk, self.hidden_lead.pk])
        )
        self.assertRedirects(response, reverse("dashboard:services"))
        self.service.refresh_from_db()
        self.assertEqual(self.service.title, "Updated service")
        self.assertEqual(self.service.image.name, "uploads/images/existing-service.png")
        self.assertCountEqual(self.service.doctors.all(), [self.visible_lead, self.hidden_lead])
        public = self.client.get(reverse("website:service_details", args=[self.service.pk]))
        self.assertCountEqual(public.context["doctors"], [self.visible_lead])
        self.assertNotContains(public, self.hidden_lead.fullname)

    def test_explicit_deselection_removes_hidden_assignment(self):
        response = self.client.post(self.url, self.payload(doctors=[self.visible_lead.pk]))
        self.assertRedirects(response, reverse("dashboard:services"))
        self.assertCountEqual(self.service.doctors.all(), [self.visible_lead])

    def test_new_hidden_assignments_are_rejected_on_create_and_edit(self):
        other_service = Service.objects.create(
            title="Another service", description="Details", schedules="Daily",
            image="uploads/images/other.png",
        )
        other_service.doctors.add(self.other_hidden_lead)
        for create in (False, True):
            with self.subTest(create=create):
                response = self.client.post(
                    self.url, self.payload(doctors=[self.other_hidden_lead.pk], create=create)
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("doctors", response.context["form"].errors)
                self.assertFalse(Service.objects.filter(title="New service").exists())
                self.assert_original_service()

    def test_malformed_nonexistent_and_out_of_range_lead_ids_do_not_partially_save(self):
        for lead_id in ("not-an-id", "999999", "9" * 100, "-1"):
            with self.subTest(lead_id=lead_id):
                response = self.client.post(
                    self.url, self.payload(doctors=[self.visible_lead.pk, lead_id])
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("doctors", response.context["form"].errors)
                self.assert_original_service()

    def test_new_assignment_hidden_after_loading_edit_form_is_rejected(self):
        candidate = self.lead("Dr Pending Assignment", visible=True)
        response = self.client.get(self.url, {"service_id": self.service.pk})
        self.assertIn(candidate, response.context["form"].fields["doctors"].queryset)
        candidate.visible = False
        candidate.save(update_fields=["visible"])
        response = self.client.post(self.url, self.payload(doctors=[candidate.pk]))
        self.assertEqual(response.status_code, 400)
        self.assert_original_service()

    def test_deleted_lead_selection_is_rejected_without_removing_other_assignments(self):
        candidate = self.lead("Dr Deleted", visible=True)
        candidate_id = candidate.pk
        candidate.delete()
        response = self.client.post(self.url, self.payload(doctors=[candidate_id]))
        self.assertEqual(response.status_code, 400)
        self.assertIn("doctors", response.context["form"].errors)
        self.assert_original_service()

    def test_invalid_image_preserves_entered_values_and_selections_without_saving(self):
        data = self.payload(doctors=[self.hidden_lead.pk])
        data.pop("visible")
        data["image"] = SimpleUploadedFile("invalid.png", b"not an image")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)
        form = response.context["form"]
        self.assertIn("image", form.errors)
        self.assertEqual(form["title"].value(), "Updated service")
        self.assertEqual(form["description"].value(), data["description"])
        self.assertEqual(form["schedules"].value(), data["schedules"])
        self.assertEqual(form["doctors"].value(), [str(self.hidden_lead.pk)])
        self.assertFalse(form["visible"].value())
        self.assertContains(response, 'value="Updated service"', status_code=400)
        self.assert_original_service()

    def test_invalid_title_preserves_selected_leads_and_visible_choice(self):
        data = self.payload(doctors=[self.hidden_lead.pk])
        data["title"] = ""
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)
        form = response.context["form"]
        self.assertIn("title", form.errors)
        self.assertEqual(form["doctors"].value(), [str(self.hidden_lead.pk)])
        self.assertTrue(form["visible"].value())
        self.assert_original_service()

    def test_invalid_service_ids_return_not_found_without_creating_or_updating(self):
        for service_id in ("not-an-id", "999999", "0", "-1", "9" * 100):
            with self.subTest(service_id=service_id):
                self.assertEqual(self.client.get(self.url, {"service_id": service_id}).status_code, 404)
                data = self.payload()
                data["service_id"] = service_id
                self.assertEqual(self.client.post(self.url, data).status_code, 404)
                self.assertEqual(Service.objects.count(), 1)
                self.assert_original_service()

    def test_unauthorized_users_cannot_change_service_or_assignments(self):
        denied_users = [
            self.user("front-desk", Administrator.Role.FRONT_DESK),
            self.user("auditor", Administrator.Role.AUDITOR),
            self.user("regular", Administrator.Role.CONTENT_MANAGER, is_staff=False),
        ]
        for user in denied_users:
            with self.subTest(role=user.role, is_staff=user.is_staff):
                self.client.force_login(user)
                response = self.client.post(self.url, self.payload())
                self.assertEqual(response.status_code, 403)
                self.assert_original_service()
        inactive = self.user("inactive", Administrator.Role.CONTENT_MANAGER, is_active=False)
        self.client.force_login(inactive)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 302)
        self.assert_original_service()

    def test_auditor_can_view_form_but_cannot_submit_and_superuser_can_clear(self):
        auditor = self.user("viewer", Administrator.Role.AUDITOR)
        self.client.force_login(auditor)
        self.assertEqual(self.client.get(self.url, {"service_id": self.service.pk}).status_code, 200)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)
        self.assert_original_service()
        superuser = self.user("super", Administrator.Role.SUPER_ADMIN, is_superuser=True)
        self.client.force_login(superuser)
        self.assertRedirects(self.client.post(self.url, self.payload()), reverse("dashboard:services"))
        self.assertFalse(self.service.doctors.exists())

    def test_csrf_protection_is_unchanged(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.manager)
        self.assertEqual(csrf_client.post(self.url, self.payload()).status_code, 403)
        self.assert_original_service()

    def test_hidden_existing_lead_reappears_publicly_only_when_made_visible(self):
        url = reverse("website:service_details", args=[self.service.pk])
        self.assertNotContains(self.client.get(url), self.hidden_lead.fullname)
        self.hidden_lead.visible = True
        self.hidden_lead.save(update_fields=["visible"])
        public = self.client.get(url)
        self.assertContains(public, self.hidden_lead.fullname)
        self.assertCountEqual(public.context["doctors"], [self.visible_lead, self.hidden_lead])

    def test_form_rejects_forged_hidden_choice_independently_of_dashboard(self):
        form = ServiceForm(self.payload(doctors=[self.other_hidden_lead.pk]), instance=self.service)
        self.assertFalse(form.is_valid())
        self.assertIn("doctors", form.errors)
        self.assert_original_service()

    def test_failed_relationship_save_rolls_back_scalar_fields_and_assignments(self):
        with patch.object(ServiceForm, "_save_m2m", side_effect=IntegrityError("Assignment changed concurrently")):
            with self.assertRaises(IntegrityError):
                self.client.post(self.url, self.payload(doctors=[self.visible_lead.pk]))
        self.assert_original_service()


@override_settings(SECURE_SSL_REDIRECT=False)
class ServiceTeamLeadApiAssignmentTests(ServiceTeamLeadAssignmentFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.manager)
        self.api_url = "/api/v1/services"

    def api_payload(self, *, doctors=None):
        data = self.payload(doctors=doctors)
        data["id"] = data.pop("service_id")
        return data

    def test_api_patch_omitted_team_leads_preserves_visible_and_hidden_associations(self):
        response = self.api_client.patch(self.api_url, self.api_payload(), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["service"]["title"], "Updated service")
        self.assertCountEqual(response.data["service"]["doctors"], [self.visible_lead.pk, self.hidden_lead.pk])
        self.assertCountEqual(self.service.doctors.all(), [self.visible_lead, self.hidden_lead])

    def test_api_multipart_patch_omission_preserves_multiple_existing_associations(self):
        response = self.api_client.patch(self.api_url, self.api_payload(), format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertIn("service", response.data)
        self.assertCountEqual(self.service.doctors.all(), [self.visible_lead, self.hidden_lead])

    def test_api_patch_explicit_empty_list_clears_all_associations(self):
        response = self.api_client.patch(self.api_url, self.api_payload(doctors=[]), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["service"]["doctors"], [])
        self.assertFalse(self.service.doctors.exists())

    def test_api_patch_valid_multiple_choice_can_preserve_hidden_and_add_visible_lead(self):
        new_lead = self.lead("Dr Newly Assigned", visible=True)
        selected = [self.visible_lead.pk, self.hidden_lead.pk, new_lead.pk]
        response = self.api_client.patch(self.api_url, self.api_payload(doctors=selected), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.data["service"]["doctors"], selected)
        self.assertCountEqual(self.service.doctors.all(), [self.visible_lead, self.hidden_lead, new_lead])

    def test_api_invalid_team_leads_keep_legacy_error_envelope_and_do_not_write(self):
        for lead_id in (self.other_hidden_lead.pk, "9" * 100, "not-an-id", "999999"):
            with self.subTest(lead_id=lead_id):
                response = self.api_client.patch(
                    self.api_url, self.api_payload(doctors=[self.visible_lead.pk, lead_id]), format="json"
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("response", response.data)
                self.assertNotIn("service", response.data)
                self.assertIn("doctors", str(response.data["response"]))
                self.assert_original_service()

    def test_api_patch_omission_without_existing_associations_remains_empty(self):
        self.service.doctors.clear()
        response = self.api_client.patch(self.api_url, self.api_payload(), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["service"]["doctors"], [])
        self.assertFalse(self.service.doctors.exists())

    def test_api_create_without_team_leads_remains_optional(self):
        response = self.api_client.post(self.api_url, self.payload(create=True), format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertIn("service", response.data)
        self.assertEqual(response.data["service"]["doctors"], [])
        self.assertFalse(Service.objects.get(title="New service").doctors.exists())

    def test_api_omitted_team_leads_do_not_overwrite_concurrent_assignment_change(self):
        concurrent_lead = self.lead("Dr Concurrent Assignment", visible=True)
        original_save = ServiceForm.save

        def save_after_assignment_change(form, *args, **kwargs):
            # Simulate a second editor changing the relationship after validation.
            self.assertNotIn("doctors", form.cleaned_data)
            self.service.doctors.set([concurrent_lead])
            return original_save(form, *args, **kwargs)

        with patch.object(ServiceForm, "save", autospec=True, side_effect=save_after_assignment_change):
            response = self.api_client.patch(self.api_url, self.api_payload(), format="json")

        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(response.data["service"]["doctors"], [concurrent_lead.pk])
        self.assertCountEqual(self.service.doctors.all(), [concurrent_lead])

    def test_api_roles_cannot_mutate_service_assignments(self):
        users = (
            self.user("api-auditor", Administrator.Role.AUDITOR),
            self.user("api-front-desk", Administrator.Role.FRONT_DESK),
            self.user("api-regular", Administrator.Role.CONTENT_MANAGER, is_staff=False),
            self.user("api-inactive", Administrator.Role.CONTENT_MANAGER, is_active=False),
            None,
        )
        for user in users:
            with self.subTest(user=user):
                self.api_client.force_authenticate(user)
                response = self.api_client.patch(self.api_url, self.api_payload(doctors=[]), format="json")
                self.assertIn(response.status_code, (401, 403))
                self.assert_original_service()
