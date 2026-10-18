from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import Administrator
from website.models import About, Contact
from website.site_settings import (
    SiteSettings, SiteSettingsForm, StaleSiteSettings,
    load_public_site_settings, normalized_phone, validate_public_url,
)


def settings_payload(instance=None, **overrides):
    form = SiteSettingsForm(instance=instance or SiteSettings())
    values = {name: form[name].value() or "" for name in form.Meta.fields}
    values["revision_token"] = form["revision_token"].value()
    values.update(overrides)
    return values


class SharedDestinationValidationTests(SimpleTestCase):
    def test_public_urls_require_explicit_http_scheme_and_no_ambiguous_characters(self):
        for value in (
            "javascript:alert(1)", "//example.test/path", "data:text/html,hello",
            "https://example.test/\nnext", "https://example.test/\tpath",
            " https://example.test",
            "https://" + "user:password@example.test/",  # Synthetic unsafe userinfo.
            "https:\\example.test/path", "https://example.test:invalid/",
            "ftp://example.test/file", "https://example.test/has space",
        ):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_public_url(value)
        for value in ("", "https://example.test/social?campaign=one&source=two", "http://example.test/profile"):
            validate_public_url(value)

    def test_normalized_telephone_rejects_executable_and_malformed_values(self):
        self.assertEqual(normalized_phone("+233 (20) 123-4567"), "+233201234567")
        for value in ("javascript:alert(1)", "+2331234;ext=9", "123", "9" * 16, "+233\n201234567"):
            with self.subTest(value=value):
                self.assertEqual(normalized_phone(value), "")


class SiteSettingsPersistenceTests(TestCase):
    def test_public_load_has_legacy_defaults_without_creating_record(self):
        result = load_public_site_settings()
        self.assertEqual(result.availability_summary, "Open 24 hours, every day")
        self.assertIn("SINELHOSPITALTEMA", result.facebook_url)
        self.assertEqual(result.telephone_href, "")
        self.assertEqual(result.map_embed_url, "")
        self.assertFalse(SiteSettings.objects.exists())

    def test_save_validate_readback_clear_and_new_revision(self):
        form = SiteSettingsForm(settings_payload(
            availability_summary="Appointments available every weekday",
            facebook_url="https://example.test/hospital", whatsapp_number="+233 20 123 4567",
            id="2", site_key="injected-site", revision="99", is_superuser="on",
        ))
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(saved.pk, 1)
        self.assertEqual(saved.site_key, "primary")
        self.assertEqual(saved.revision, 1)
        clear = SiteSettingsForm(settings_payload(saved, facebook_url=""), instance=saved)
        self.assertTrue(clear.is_valid(), clear.errors)
        clear.save()
        self.assertEqual(load_public_site_settings().facebook_url, "")
        saved.refresh_from_db()
        self.assertEqual(saved.revision, 2)

    def test_stale_existing_form_cannot_overwrite_newer_save(self):
        saved = SiteSettings.objects.create()
        stale_payload = settings_payload(saved, availability_summary="Older proposed statement")
        fresh = SiteSettingsForm(settings_payload(saved, availability_summary="Current statement"), instance=saved)
        self.assertTrue(fresh.is_valid(), fresh.errors)
        fresh.save()
        stale = SiteSettingsForm(stale_payload, instance=SiteSettings.objects.get(pk=1))
        self.assertTrue(stale.is_valid(), stale.errors)
        with self.assertRaises(StaleSiteSettings):
            stale.save()
        self.assertEqual(SiteSettings.objects.get(pk=1).availability_summary, "Current statement")

    def test_two_initial_forms_cannot_create_duplicate_settings(self):
        payload = settings_payload()
        first = SiteSettingsForm(payload)
        second = SiteSettingsForm(payload)
        self.assertTrue(first.is_valid(), first.errors)
        self.assertTrue(second.is_valid(), second.errors)
        first.save()
        with self.assertRaises(StaleSiteSettings):
            second.save()
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_database_rejects_other_singleton_identity(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SiteSettings.objects.create(pk=2)

    def test_signed_revision_required_and_invalid_form_preserves_values(self):
        for token in ("", "not-a-signed-token"):
            form = SiteSettingsForm(settings_payload(revision_token=token))
            self.assertFalse(form.is_valid())
            self.assertIn("revision_token", form.errors)
        form = SiteSettingsForm(settings_payload(
            availability_summary="Please retain this attempted wording",
            facebook_url="https://example.test/\ninvalid",
        ))
        self.assertFalse(form.is_valid())
        self.assertEqual(form["availability_summary"].value(), "Please retain this attempted wording")
        self.assertFalse(SiteSettings.objects.exists())

    def test_bounds_and_optional_whatsapp_have_server_validation(self):
        for field, value in (
            ("availability_summary", "x" * 121), ("availability_summary", "   "),
            ("whatsapp_number", "not a number"), ("facebook_url", "https://example.test/" + "x" * 300),
        ):
            with self.subTest(field=field):
                form = SiteSettingsForm(settings_payload(**{field: value}))
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_destinations_use_contact_coordinates_address_and_separate_whatsapp(self):
        SiteSettings.objects.create(whatsapp_number="+233 20 765 4321")
        contact = SimpleNamespace(
            telephone="+233 (20) 123-4567", email="care+desk@example.test",
            lat_lng="5.6698, -0.0166", address="42 Fictional Way, Example City",
        )
        result = load_public_site_settings(contact=contact)
        self.assertEqual(result.telephone_href, "tel:+233201234567")
        self.assertEqual(result.email_href, "mailto:care+desk@example.test")
        self.assertIn("phone=233207654321", result.whatsapp_url)
        self.assertIn("query=5.6698%2C-0.0166", result.directions_url)
        self.assertIn("q=5.6698%2C-0.0166", result.map_embed_url)
        contact.lat_lng = "999,invalid"
        result = load_public_site_settings(contact=contact)
        self.assertIn("query=42+Fictional+Way%2C+Example+City", result.directions_url)

    def test_legacy_unsafe_links_are_not_emitted_and_missing_whatsapp_uses_contact(self):
        SiteSettings.objects.create(facebook_url="javascript:alert(1)", instagram_url="", youtube_url="")
        result = load_public_site_settings(contact=SimpleNamespace(telephone="+233201234567", email="bad\n@example.test"))
        self.assertEqual(result.facebook_url, "")
        self.assertEqual(result.email_href, "")
        self.assertIn("phone=233201234567", result.whatsapp_url)


class SiteSettingsDashboardTests(TestCase):
    def setUp(self):
        self.manager = Administrator.objects.create_user(
            email_address="settings-manager@example.test", password=None,
            fullname="Fictional content manager", is_staff=True, is_active=True,
            role=Administrator.Role.CONTENT_MANAGER,
        )
        self.url = reverse("dashboard:site_settings")

    def test_editor_get_does_not_create_and_successful_save_updates_public_footer(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SiteSettings.objects.exists())
        payload = settings_payload(facebook_url="https://example.test/new-social", instagram_url="", youtube_url="")
        response = self.client.post(self.url, payload)
        self.assertRedirects(response, self.url)
        public = self.client.get(reverse("website:index"))
        self.assertContains(public, "https://example.test/new-social")
        self.assertNotContains(public, "https://www.instagram.com/sinelhospital/")

    def test_invalid_save_retains_input_without_mutation_and_stale_save_returns_409(self):
        saved = SiteSettings.objects.create()
        self.client.force_login(self.manager)
        response = self.client.post(self.url, settings_payload(saved, facebook_url="javascript:alert(1)", availability_summary="Keep my proposed copy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Keep my proposed copy")
        saved.refresh_from_db()
        self.assertEqual(saved.revision, 1)
        old = settings_payload(saved)
        SiteSettings.objects.filter(pk=1).update(revision=2, availability_summary="Saved by another editor")
        response = self.client.post(self.url, old)
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "changed while you were editing", status_code=409)
        self.assertEqual(SiteSettings.objects.get(pk=1).availability_summary, "Saved by another editor")

    def test_anonymous_wrong_role_and_readonly_auditor_cannot_write(self):
        response = self.client.post(self.url, settings_payload())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)
        for role in (Administrator.Role.FRONT_DESK, Administrator.Role.AUDITOR):
            user = Administrator.objects.create_user(
                email_address=f"settings-{role}@example.test", password=None,
                is_staff=True, is_active=True, role=role,
            )
            self.client.force_login(user)
            self.assertEqual(self.client.post(self.url, settings_payload()).status_code, 403)
        self.assertFalse(SiteSettings.objects.exists())

    def test_contact_footer_links_use_validated_source_and_about_statistics_are_not_duplicated(self):
        Contact.objects.create(
            address="42 Fictional Way", gps="EX-000-0000", email="care@example.test",
            telephone="+233 20 123 4567", lat_lng="5.6698,-0.0166",
        )
        About.objects.create(years_value="42+", availability_value="Daily")
        response = self.client.get(reverse("website:index"))
        self.assertContains(response, 'href="tel:+233201234567"')
        self.assertContains(response, 'href="mailto:care@example.test"')
        self.assertNotIn("years_value", SiteSettingsForm.Meta.fields)
        self.assertNotIn("availability_value", SiteSettingsForm.Meta.fields)
