from io import BytesIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.shortcuts import reverse
from django.test import Client, RequestFactory, TestCase
from django.urls import resolve
from PIL import Image

from accounts.models import Administrator
from blog.models import Page, Post
from website.models import Service
from website.page_content import (
    METADATA_ROUTES, SECTION_REGISTRY, PageMetadata, PageMetadataForm,
    PageSection, PageSectionForm, metadata_for_request, public_sections,
)


class PageContentTests(TestCase):
    def setUp(self):
        self.editor = Administrator.objects.create_user(
            email_address="copy.editor@example.test", password="fictional-local-only",
            fullname="Fictional Editor", is_staff=True,
            role=Administrator.Role.CONTENT_MANAGER,
        )
        self.client.force_login(self.editor)

    def edit_url(self, key="about_principles"):
        return reverse("dashboard:page_content_edit", args=[key])

    def payload(self, key, **overrides):
        response = self.client.get(self.edit_url(key))
        form = response.context["form"]
        data = {name: form[name].value() or "" for name in form.fields if name not in {"image", "image_alt"}}
        data.update(overrides)
        return data

    def test_default_registry_fits_contract_and_get_does_not_write(self):
        for key, spec in SECTION_REGISTRY.items():
            instance = PageSection(key=key, eyebrow=spec.eyebrow, title=spec.title, body=spec.body)
            instance.full_clean()
            self.assertEqual(self.client.get(self.edit_url(key)).status_code, 200)
        self.assertEqual(PageSection.objects.count(), 0)
        self.assertEqual(self.client.get(reverse("dashboard:page_content")).status_code, 200)
        self.assertEqual(PageSection.objects.count(), 0)
        self.assertEqual(public_sections()["about_principles"].title, "Our story, focus and people")

    def test_save_normalizes_and_public_projection_escapes_plain_text(self):
        data = self.payload("team_intro", title="  Fictional  care\nteam ", body="Helpful <script>alert(1)</script> text")
        response = self.client.post(self.edit_url("team_intro"), data)
        self.assertEqual(response.status_code, 302)
        row = PageSection.objects.get(key="team_intro")
        self.assertEqual(row.title, "Fictional care team")
        public = self.client.get(reverse("website:doctors"))
        self.assertContains(public, "Fictional care team")
        self.assertContains(public, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(public, "<script>alert(1)</script>")

    def test_character_bounds_unicode_and_whitespace(self):
        key = "about_highlight_family"
        data = self.payload(key, title="😀" * 45)
        response = self.client.post(self.edit_url(key), data)
        self.assertEqual(response.status_code, 302)
        data = self.payload(key, title="W" * 46, body="Retain this attempted text")
        response = self.client.post(self.edit_url(key), data)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Retain this attempted text", status_code=400)
        self.assertEqual(PageSection.objects.get(key=key).title, "😀" * 45)
        data = self.payload(key, title=" \n\t ")
        response = self.client.post(self.edit_url(key), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("title", response.context["form"].errors)

    def test_help_counter_and_errors_are_associated_without_javascript(self):
        response = self.client.get(self.edit_url("about_highlight_family"))
        self.assertContains(response, 'aria-describedby="id_title_helptext id_title_count"')
        self.assertContains(response, 'id="id_title_count"')
        data = self.payload("about_highlight_family", title="W" * 46)
        response = self.client.post(self.edit_url("about_highlight_family"), data)
        self.assertContains(response, 'aria-describedby="id_title_helptext id_title_count id_title_error"', status_code=400)
        self.assertContains(response, 'id="id_title_error"', status_code=400)

    def test_stale_same_section_is_conflict_and_preserves_attempt(self):
        older = self.payload("about_principles", title="Old attempted heading")
        newer = self.payload("about_principles", title="New committed heading")
        self.assertEqual(self.client.post(self.edit_url(), newer).status_code, 302)
        response = self.client.post(self.edit_url(), older)
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "Old attempted heading", status_code=409)
        row = PageSection.objects.get(key="about_principles")
        self.assertEqual(row.title, "New committed heading")
        self.assertEqual(PageSection.objects.count(), 1)
        # A persisted revision cannot be replayed after another save, either.
        payload = self.payload("about_principles", title="Second saved heading")
        self.assertEqual(self.client.post(self.edit_url(), payload).status_code, 302)
        self.assertEqual(self.client.post(self.edit_url(), payload).status_code, 409)

    def test_independent_sections_do_not_overwrite_each_other(self):
        first = self.payload("about_principles", title="Principles changed")
        second = self.payload("about_intro", title="Overview changed")
        self.assertEqual(self.client.post(self.edit_url("about_principles"), first).status_code, 302)
        self.assertEqual(self.client.post(self.edit_url("about_intro"), second).status_code, 302)
        self.assertEqual(PageSection.objects.get(key="about_principles").title, "Principles changed")
        self.assertEqual(PageSection.objects.get(key="about_intro").title, "Overview changed")

    def test_unverified_or_cross_section_token_cannot_save(self):
        data = self.payload("team_intro", revision_token="invalid-signature")
        self.assertEqual(self.client.post(self.edit_url("team_intro"), data).status_code, 409)
        other = self.payload("gallery_intro")
        self.assertEqual(self.client.post(self.edit_url("team_intro"), other).status_code, 409)
        self.assertEqual(PageSection.objects.count(), 0)

    def test_unknown_key_and_mass_assignment_not_permitted(self):
        self.assertEqual(self.client.get(self.edit_url("arbitrary_section")).status_code, 404)
        self.assertEqual(self.client.post(self.edit_url("arbitrary_section"), {}).status_code, 404)
        data = self.payload("team_intro", title="Allowed heading", revision=999, is_superuser="true")
        data["key"] = "about_intro"
        self.assertEqual(self.client.post(self.edit_url("team_intro"), data).status_code, 302)
        row = PageSection.objects.get()
        self.assertEqual(row.key, "team_intro")
        self.assertEqual(row.revision, 1)
        self.editor.refresh_from_db()
        self.assertFalse(self.editor.is_superuser)

    def test_read_only_and_unauthorized_roles(self):
        data = self.payload("team_intro")
        self.editor.role = Administrator.Role.AUDITOR
        self.editor.save(update_fields=["role"])
        self.assertEqual(self.client.get(self.edit_url("team_intro")).status_code, 200)
        self.assertEqual(self.client.post(self.edit_url("team_intro"), data).status_code, 403)
        self.editor.role = Administrator.Role.FRONT_DESK
        self.editor.save(update_fields=["role"])
        self.assertEqual(self.client.get(self.edit_url("team_intro")).status_code, 403)
        self.assertEqual(self.client.post(self.edit_url("team_intro"), data).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.edit_url("team_intro")).status_code, 302)
        self.assertEqual(PageSection.objects.count(), 0)

    def test_csrf_rejection_does_not_write(self):
        guarded = Client(enforce_csrf_checks=True)
        guarded.force_login(self.editor)
        data = self.payload("team_intro")
        self.assertEqual(guarded.post(self.edit_url("team_intro"), data).status_code, 403)
        self.assertEqual(PageSection.objects.count(), 0)

    def test_intro_updates_reach_each_public_listing_without_code_changes(self):
        cases = [
            ("contact_intro", "website:contact"),
            ("gallery_intro", "website:gallery"),
            ("team_intro", "website:doctors"),
            ("partners_intro", "website:partners"),
            ("services_intro", "website:services"),
            ("news_intro", "blog:posts"),
            ("booking_intro", "communications:book_appointment"),
        ]
        for key, route in cases:
            with self.subTest(section=key):
                heading = "Fictional " + key.replace("_", " ")
                data = self.payload(key, title=heading)
                self.assertEqual(self.client.post(self.edit_url(key), data).status_code, 302)
                page = self.client.get(reverse(route))
                self.assertContains(page, heading)
        # The operational confirmation and emergency consequences remain fixed.
        booking = self.client.get(reverse("communications:book_appointment"))
        self.assertContains(booking, "Our team will contact you to confirm the appointment.")
        self.assertContains(booking, "Come to the hospital immediately.")

    def test_image_only_supported_for_home_story(self):
        form = PageSectionForm(section_key="home_story", instance=PageSection(key="home_story"))
        self.assertIn("image", form.fields)
        self.assertNotIn("body", form.fields)
        other = PageSectionForm(section_key="team_intro", instance=PageSection(key="team_intro"))
        self.assertNotIn("image", other.fields)
        self.assertNotIn("image_alt", other.fields)

    def image_upload(self, name="fictional.png", padding=0):
        buffer = BytesIO()
        Image.new("RGB", (12, 8), color="blue").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue() + b" " * padding, content_type="image/png")

    def test_image_replacement_retention_clear_and_rejection(self):
        data = self.payload("home_story", image_alt="Fictional hospital exterior")
        data["image"] = self.image_upload()
        self.assertEqual(self.client.post(self.edit_url("home_story"), data).status_code, 302)
        row = PageSection.objects.get(key="home_story")
        original_name = row.image.name
        self.assertTrue(original_name.endswith(".png"))
        self.assertEqual(public_sections()["home_story"].image_alt, "Fictional hospital exterior")
        data = self.payload("home_story", title="New heading without replacement")
        self.assertEqual(self.client.post(self.edit_url("home_story"), data).status_code, 302)
        row.refresh_from_db()
        self.assertEqual(row.image.name, original_name)
        data = self.payload("home_story", title="W" * 111, image=self.image_upload("not-saved.png"))
        self.assertEqual(self.client.post(self.edit_url("home_story"), data).status_code, 400)
        row.refresh_from_db()
        self.assertEqual(row.image.name, original_name)
        data = self.payload("home_story", image=self.image_upload(padding=5 * 1024 * 1024))
        self.assertEqual(self.client.post(self.edit_url("home_story"), data).status_code, 400)
        row.refresh_from_db()
        self.assertEqual(row.image.name, original_name)
        data = self.payload("home_story", **{"image-clear": "on"})
        self.assertEqual(self.client.post(self.edit_url("home_story"), data).status_code, 302)
        row.refresh_from_db()
        self.assertFalse(row.image)

    def test_unsupported_image_payload_does_not_write(self):
        data = self.payload("home_story", image=SimpleUploadedFile("bad.svg", b'<svg onload="alert(1)"></svg>', content_type="image/svg+xml"))
        response = self.client.post(self.edit_url("home_story"), data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("image", response.context["form"].errors)
        self.assertEqual(PageSection.objects.count(), 0)

    def test_image_storage_failure_rolls_back_and_retains_text(self):
        data = self.payload("home_story", title="Retained fictional story", image=self.image_upload())
        storage = PageSection._meta.get_field("image").storage
        with patch.object(storage, "save", side_effect=OSError("fictional storage failure")):
            response = self.client.post(self.edit_url("home_story"), data)
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "Retained fictional story", status_code=503)
        self.assertEqual(PageSection.objects.count(), 0)

    def test_model_rejects_unknown_keys_and_out_of_contract_fields(self):
        with self.assertRaises(ValidationError):
            PageSection(key="anything", title="No").full_clean()
        with self.assertRaises(ValidationError):
            PageSection(key="home_story", title="Story", body="Must reuse About overview").full_clean()


class PageMetadataTests(TestCase):
    def setUp(self):
        self.editor = Administrator.objects.create_user(
            email_address="metadata.editor@example.test", password="fictional-local-only",
            fullname="Fictional Metadata Editor", is_staff=True,
        )
        self.client.force_login(self.editor)

    def url(self, key="about"):
        return reverse("dashboard:page_metadata_edit", args=[key])

    def payload(self, key="about", **updates):
        form = self.client.get(self.url(key)).context["form"]
        data = {name: form[name].value() or "" for name in form.fields}
        data.update(updates)
        return data

    def test_metadata_save_readback_clear_defaults_and_no_get_writes(self):
        for key in METADATA_ROUTES:
            self.assertEqual(self.client.get(self.url(key)).status_code, 200)
        self.assertEqual(PageMetadata.objects.count(), 0)
        data = self.payload(title="Fictional page title", description="A short fictional page description.")
        self.assertEqual(self.client.post(self.url(), data).status_code, 302)
        page = self.client.get(reverse("website:about"))
        self.assertContains(page, "Fictional page title")
        self.assertContains(page, 'content="A short fictional page description."')
        data = self.payload(title="", description="")
        self.assertEqual(self.client.post(self.url(), data).status_code, 302)
        page = self.client.get(reverse("website:about"))
        self.assertContains(page, "About | Sinel Specialist Hospital")

    def test_bounds_conflicts_invalid_keys_and_escaping(self):
        first = self.payload(title="First saved title", description='A "quoted" description')
        stale = self.payload(title="Stale title")
        self.assertEqual(self.client.post(self.url(), first).status_code, 302)
        self.assertEqual(self.client.post(self.url(), stale).status_code, 409)
        invalid = self.payload(description="W" * 161)
        self.assertEqual(self.client.post(self.url(), invalid).status_code, 400)
        self.assertEqual(PageMetadata.objects.get().title, "First saved title")
        page = self.client.get(reverse("website:about"))
        self.assertContains(page, "A &quot;quoted&quot; description")
        self.assertEqual(self.client.get(self.url("unregistered")).status_code, 404)

    def metadata(self, path):
        request = RequestFactory().get(path)
        request.resolver_match = resolve(path)
        return metadata_for_request(request)

    def test_hidden_or_malformed_detail_identifiers_never_leak_metadata(self):
        service = Service.objects.create(title="Secret fictional service", description="Secret service text", schedules="Daily", image="fictional.jpg", visible=False)
        post = Post.objects.create(title="Secret fictional article", content="Secret article text", thumbnail="fictional.jpg", tags="fictional", by=self.editor, visible=False)
        page = Page.objects.create(title="Secret fictional page", content="Secret page text", by=self.editor, visible=False)
        paths = [
            reverse("website:service_details", args=[service.pk]),
            reverse("blog:post_detail", args=[post.pk]),
            reverse("website:static_page_view", args=[page.pk, page.slug]),
            reverse("website:service_details", args=["9" * 200]),
        ]
        for path in paths:
            result = self.metadata(path)
            self.assertNotIn("Secret", result["title"])
            self.assertNotIn("Secret", result["description"])
        service.visible = True
        service.save(update_fields=["visible"])
        result = self.metadata(paths[0])
        self.assertIn(service.title, result["title"])
        self.assertEqual(result["description"], "Secret service text")
