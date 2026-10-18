from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import Administrator
from blog.models import Page, Post
from dashboard.editor_state import CONFLICT_MESSAGE
from website.models import About, Album, Award, Banner, Contact, HomepageShortcut, HomepageVideo, Media, Notification, Partner, Service, TeamLead, Testimonial


@override_settings(SECURE_SSL_REDIRECT=False)
class EditorIntegrityTests(TestCase):
    def setUp(self):
        media_directory = TemporaryDirectory()
        self.addCleanup(media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.manager = self.user("editor")
        self.author = self.user("original-author")
        self.client.force_login(self.manager)
        self.partner = Partner.objects.create(
            name="Fictional partner", category="Corporate Partners", description="Original description",
            website="https://partner.example.test", logo="partner.png", visible=True,
        )
        self.service = Service.objects.create(title="Existing service", description="Details", image="service.png", visible=True)
        self.hidden_service = Service.objects.create(title="Hidden service", description="Details", image="service.png", visible=False)
        self.lead = TeamLead.objects.create(fullname="Visible lead", title="Nurse", bio="Biography", photo="lead.png", visible=True)
        self.hidden_lead = TeamLead.objects.create(fullname="Hidden lead", title="Nurse", bio="Biography", photo="lead.png", visible=False)
        self.testimonial = Testimonial.objects.create(username="Fictional patient", message="Original experience", service=self.hidden_service, doctor=self.hidden_lead, photo="testimonial.png", added_by=self.author, visible=True)
        self.post = Post.objects.create(title="Original article", content="<p>Original article content</p>", thumbnail="post.png", tags="Health", by=self.author, visible=True)
        self.page = Page.objects.create(title="Original page", content="<p>Original page content</p>", by=self.author, visible=True)
        self.album = Album.objects.create(name="Fictional album")
        self.media = Media.objects.create(name="Original media", description="Original caption", album=self.album, file="media.png", visible=True)
        self.notification = Notification.objects.create(title="Original notification", message="Original message", available_at="2026-10-01T10:00:00Z", expires_at="2026-11-01T10:00:00Z")

    @staticmethod
    def user(name, role=Administrator.Role.CONTENT_MANAGER):
        return Administrator.objects.create_user(email_address=f"integrity-{name}@example.test", password=None, fullname=name, is_staff=True, is_active=True, role=role)

    @staticmethod
    def image_upload():
        buffer = BytesIO()
        Image.new("RGB", (16, 16), "blue").save(buffer, format="PNG")
        return SimpleUploadedFile("replacement.png", buffer.getvalue(), content_type="image/png")

    def edit(self, kind, data, instance=None, token=None, **kwargs):
        route = "contact" if kind == "contact" else f"create_update_{kind}"
        url = reverse(f"dashboard:{route}")
        identifier = f"{kind}_id"
        if token is None:
            response = self.client.get(url, {identifier: instance.pk} if instance else {})
            self.assertEqual(response.status_code, 200)
            token = response.context["editor_revision"]
        payload = {**data, "editor_revision": token}
        if instance:
            payload[identifier] = instance.pk
        return self.client.post(url, payload, **kwargs)

    def partner_payload(self):
        return {"name": "Edited partner", "category": "Corporate Partners", "description": "Original description", "website": "https://partner.example.test", "visible": "on"}

    def testimonial_payload(self):
        return {"username": "Edited patient", "message": "Edited experience", "service": self.hidden_service.pk, "doctor": self.hidden_lead.pk, "visible": "on"}

    def cases(self):
        return [
            ("partner", self.partner, self.partner_payload(), "name"),
            ("testimonial", self.testimonial, self.testimonial_payload(), "username"),
            ("post", self.post, {"title": "Edited article", "content": "<p>Edited article content</p>", "tags": "Care", "visible": "on"}, "title"),
            ("page", self.page, {"title": "Edited page", "content": "<p>Edited page content</p>", "visible": "on"}, "title"),
            ("media", self.media, {"name": "Edited media", "description": "Edited caption", "album": self.album.pk, "visible": "on"}, "name"),
            ("notification", self.notification, {"title": "Edited notice", "message": "Edited message", "available_at": "2026-10-01T10:00", "expires_at": "2026-11-01T10:00"}, "title"),
        ]

    def test_partner_editor_retains_category_and_exposes_public_fields(self):
        response = self.client.get(reverse("dashboard:create_update_partner"), {"partner_id": self.partner.pk})
        self.assertEqual(response.context["form"]["category"].value(), "Corporate Partners")
        self.assertContains(response, '<option value="Corporate Partners" selected>')
        self.assertContains(response, 'name="description"')
        self.assertContains(response, 'name="website"')
        response = self.edit("partner", self.partner_payload(), self.partner)
        self.assertEqual(response.status_code, 302)
        self.partner.refresh_from_db()
        self.assertEqual(self.partner.description, "Original description")
        self.assertEqual(self.partner.website, "https://partner.example.test")
        self.assertEqual(self.partner.logo.name, "partner.png")
        self.assertEqual(self.partner.category, "Corporate Partners")

    def test_partner_can_clear_optional_content_and_hide(self):
        response = self.edit("partner", {**self.partner_payload(), "description": "", "website": "", "visible": ""}, self.partner)
        self.assertEqual(response.status_code, 302)
        self.partner.refresh_from_db()
        self.assertFalse(self.partner.description)
        self.assertFalse(self.partner.website)
        self.assertFalse(self.partner.visible)
        self.assertNotContains(self.client.get(reverse("website:partners")), "Edited partner")

    def test_partner_legacy_category_is_preserved_and_unknown_new_choice_rejected(self):
        self.partner.category = "Financial Partnerss"
        self.partner.save()
        response = self.edit("partner", {**self.partner_payload(), "category": "Financial Partnerss"}, self.partner)
        self.assertEqual(response.status_code, 302)
        self.partner.refresh_from_db()
        self.assertEqual(self.partner.category, "Financial Partnerss")
        response = self.edit("partner", {**self.partner_payload(), "category": "Forged category"}, self.partner)
        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.context["form"].errors)
        self.partner.refresh_from_db()
        self.assertEqual(self.partner.category, "Financial Partnerss")

    def test_partner_rejects_unsafe_web_destination_without_partial_save(self):
        for url in ("javascript:alert(1)", "ftp://example.test/file", "//example.test"):
            with self.subTest(url=url):
                response = self.edit("partner", {**self.partner_payload(), "website": url}, self.partner)
                self.assertEqual(response.status_code, 400)
                self.assertIn("website", response.context["form"].errors)
                self.partner.refresh_from_db()
                self.assertEqual(self.partner.name, "Fictional partner")

    def test_testimonial_optional_associations_preserve_only_existing_hidden_targets(self):
        response = self.client.get(reverse("dashboard:create_update_testimonial"), {"testimonial_id": self.testimonial.pk})
        form = response.context["form"]
        self.assertFalse(form.fields["service"].required)
        self.assertFalse(form.fields["doctor"].required)
        self.assertEqual(form.fields["doctor"].label, "Team Lead")
        self.assertContains(response, "Hidden lead (hidden)")
        self.assertContains(response, 'name="photo"')
        self.assertEqual(self.edit("testimonial", self.testimonial_payload(), self.testimonial).status_code, 302)
        self.testimonial.refresh_from_db()
        self.assertEqual(self.testimonial.service_id, self.hidden_service.pk)
        self.assertEqual(self.testimonial.doctor_id, self.hidden_lead.pk)
        self.assertEqual(self.testimonial.added_by, self.author)
        other_hidden = Service.objects.create(title="Other hidden", description="Other", image="other.png")
        response = self.edit("testimonial", {**self.testimonial_payload(), "service": other_hidden.pk}, self.testimonial)
        self.assertEqual(response.status_code, 400)
        self.assertIn("service", response.context["form"].errors)

    def test_testimonial_clear_and_create_without_associations(self):
        data = {"username": "Independent patient", "message": "Independent experience", "service": "", "doctor": "", "visible": "on"}
        self.assertEqual(self.edit("testimonial", data, self.testimonial).status_code, 302)
        self.testimonial.refresh_from_db()
        self.assertIsNone(self.testimonial.service_id)
        self.assertIsNone(self.testimonial.doctor_id)
        self.assertEqual(self.edit("testimonial", {**data, "username": "New patient"}).status_code, 302)
        self.assertIsNone(Testimonial.objects.get(username="New patient").service_id)

    def test_testimonial_cannot_newly_assign_hidden_or_deleted_targets(self):
        for value in (self.hidden_service.pk, "missing", "9" * 100):
            response = self.edit("testimonial", {"username": "Rejected patient", "message": "Experience", "service": value})
            self.assertEqual(response.status_code, 400)
            self.assertIn("service", response.context["form"].errors)
        self.assertFalse(Testimonial.objects.filter(username="Rejected patient").exists())

    def test_testimonial_can_replace_photo_and_failed_upload_keeps_original(self):
        response = self.edit("testimonial", {**self.testimonial_payload(), "photo": SimpleUploadedFile("bad.png", b"invalid")}, self.testimonial)
        self.assertEqual(response.status_code, 400)
        self.assertIn("photo", response.context["form"].errors)
        self.testimonial.refresh_from_db()
        self.assertEqual(self.testimonial.photo.name, "testimonial.png")
        response = self.edit("testimonial", {**self.testimonial_payload(), "photo": self.image_upload()}, self.testimonial)
        self.assertEqual(response.status_code, 302)
        self.testimonial.refresh_from_db()
        self.assertNotEqual(self.testimonial.photo.name, "testimonial.png")

    def test_author_is_preserved_for_blog_and_page_edits(self):
        for kind, instance, data, _ in self.cases():
            if kind in {"post", "page"}:
                with self.subTest(kind=kind):
                    self.assertEqual(self.edit(kind, data, instance).status_code, 302)
                    instance.refresh_from_db()
                    self.assertEqual(instance.by_id, self.author.pk)

    def test_new_blog_and_page_assign_current_author(self):
        self.assertEqual(self.edit("post", {"title": "New article", "content": "Content", "tags": "Care", "thumbnail": self.image_upload()}).status_code, 302)
        self.assertEqual(Post.objects.get(title="New article").by, self.manager)
        self.assertEqual(self.edit("page", {"title": "New page", "content": "Content"}).status_code, 302)
        self.assertEqual(Page.objects.get(title="New page").by, self.manager)

    def test_all_repaired_editors_retain_bound_input_on_rejection(self):
        for kind, instance, data, required in self.cases():
            with self.subTest(editor=kind):
                original = type(instance).objects.filter(pk=instance.pk).values().get()
                response = self.edit(kind, {**data, required: ""}, instance)
                self.assertEqual(response.status_code, 400)
                self.assertIn(required, response.context["form"].errors)
                self.assertEqual(response.context["form"][required].value(), "")
                self.assertEqual(type(instance).objects.filter(pk=instance.pk).values().get(), original)
                self.assertContains(response, "Your changes have not been saved", status_code=400)
                self.assertTrue(response.context["editor_revision"])

    def test_each_editor_rejects_stale_and_replayed_revision_without_overwrite(self):
        for kind, instance, data, name in self.cases():
            with self.subTest(editor=kind):
                url = reverse(f"dashboard:create_update_{kind}")
                editor = self.client.get(url, {f"{kind}_id": instance.pk})
                token = editor.context["editor_revision"]
                self.assertEqual(self.edit(kind, data, instance, token=token).status_code, 302)
                response = self.edit(kind, {**data, name: "Stale overwrite"}, instance, token=token)
                self.assertEqual(response.status_code, 409)
                self.assertContains(response, CONFLICT_MESSAGE, status_code=409)
                self.assertEqual(response.context["editor_revision"], token)
                self.assertEqual(response.context["form"][name].value(), "Stale overwrite")
                instance.refresh_from_db()
                self.assertEqual(getattr(instance, name), data[name])

    def test_missing_or_forged_revision_cannot_update_existing_content(self):
        url = reverse("dashboard:create_update_partner")
        for token in ("", "forged"):
            response = self.client.post(url, {**self.partner_payload(), "partner_id": self.partner.pk, "editor_revision": token})
            self.assertEqual(response.status_code, 409)
            self.partner.refresh_from_db()
            self.assertEqual(self.partner.name, "Fictional partner")

    def test_contact_empty_get_is_read_only_and_optional_metadata_can_clear(self):
        response = self.client.get(reverse("dashboard:contact"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), 0)
        data = {"email": "hello@example.test", "address": "Fictional Hospital, Ghana", "telephone": "+233200000000", "gps": "", "lat_lng": ""}
        self.assertEqual(self.edit("contact", data).status_code, 302)
        contact = Contact.objects.get()
        self.assertEqual(contact.gps, "")
        self.assertEqual(contact.lat_lng, "")
        self.assertEqual(self.edit("contact", {**data, "gps": "AB-123", "lat_lng": "5.67, -0.02"}).status_code, 302)
        self.assertEqual(self.edit("contact", data).status_code, 302)
        contact.refresh_from_db()
        self.assertEqual(contact.gps, "")
        self.assertEqual(contact.lat_lng, "")

    def test_invalid_contact_fields_retain_input_and_create_nothing(self):
        valid = {"email": "hello@example.test", "address": "Fictional Hospital", "telephone": "+233200000000", "gps": "", "lat_lng": ""}
        for name, value in (("email", "invalid"), ("address", " "), ("telephone", "call us"), ("telephone", "+233\n200000000"), ("telephone", "+233.200000000"), ("lat_lng", "NaN, 1"), ("lat_lng", "91, 1"), ("lat_lng", "1, 181"), ("lat_lng", "not coordinates")):
            with self.subTest(field=name, value=value):
                response = self.edit("contact", {**valid, name: value})
                self.assertEqual(response.status_code, 400)
                self.assertIn(name, response.context["form"].errors)
                self.assertEqual(response.context["form"][name].value(), value)
                self.assertFalse(Contact.objects.exists())

    def test_contact_exponent_coordinates_are_saved_in_map_compatible_format(self):
        response = self.edit("contact", {"email": "hello@example.test", "address": "Fictional Hospital", "telephone": "+233 200-000-000", "lat_lng": "5.67e0, -2e-2"})
        self.assertEqual(response.status_code, 302)
        contact = Contact.objects.get()
        self.assertEqual(contact.lat_lng, "5.67, -0.02")
        from website.site_settings import load_public_site_settings
        settings = load_public_site_settings(contact)
        self.assertIn("5.67%2C-0.02", settings.directions_url)
        self.assertEqual(settings.telephone_href, "tel:+233200000000")

    def test_contact_stale_empty_installation_cannot_overwrite_new_singleton(self):
        token = self.client.get(reverse("dashboard:contact")).context["editor_revision"]
        data = {"email": "hello@example.test", "address": "First contact", "telephone": "+233200000000"}
        self.assertEqual(self.edit("contact", data, token=token).status_code, 302)
        self.assertEqual(self.edit("contact", {**data, "address": "Stale first contact"}, token=token).status_code, 409)
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Contact.objects.get().address, "First contact")

    def test_notification_rejects_invalid_schedule_without_saving(self):
        data = {"title": "Attempted notice", "message": "Message", "available_at": "2026-10-02T10:00", "expires_at": "2026-10-01T10:00"}
        response = self.edit("notification", data, self.notification)
        self.assertEqual(response.status_code, 400)
        self.assertIn("expires_at", response.context["form"].errors)
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.title, "Original notification")

    def test_about_conflicts_are_section_scoped_and_keep_stale_input(self):
        about = About.objects.create(overview="Original overview", mission="Original mission", vision="Original vision", value="Original values")
        url = reverse("dashboard:about")
        editor = self.client.get(url)
        overview_token = editor.context["overview_form"].editor_revision
        mission_token = editor.context["mission_form"].editor_revision
        self.assertEqual(self.client.post(url, {"section": "overview", "overview": "First overview", "editor_revision": overview_token}).status_code, 302)
        self.assertEqual(self.client.post(url, {"section": "mission", "mission": "Concurrent mission", "editor_revision": mission_token}).status_code, 302)
        response = self.client.post(url, {"section": "overview", "overview": "Stale overview", "editor_revision": overview_token})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.context["overview_form"].editor_revision, overview_token)
        self.assertEqual(response.context["overview_form"]["overview"].value(), "Stale overview")
        about.refresh_from_db()
        self.assertEqual(about.overview, "First overview")
        self.assertEqual(about.mission, "Concurrent mission")

    def test_bad_ids_and_wrong_roles_cannot_mutate_repaired_editors(self):
        for kind, instance, data, _ in self.cases():
            url = reverse(f"dashboard:create_update_{kind}")
            for bad_id in ("bad", "9" * 100, "-1", "999999"):
                self.assertEqual(self.client.get(url, {f"{kind}_id": bad_id}).status_code, 404)
                self.assertEqual(self.client.post(url, {**data, f"{kind}_id": bad_id}).status_code, 404)
        self.client.force_login(self.user("front-desk", Administrator.Role.FRONT_DESK))
        for kind, instance, data, _ in self.cases():
            self.assertEqual(self.client.post(reverse(f"dashboard:create_update_{kind}"), {**data, f"{kind}_id": instance.pk}).status_code, 403)

    def test_csrf_still_protects_editor_saves(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.manager)
        self.assertEqual(client.post(reverse("dashboard:create_update_partner"), self.partner_payload()).status_code, 403)

    def test_remaining_content_editors_reject_same_field_stale_updates(self):
        banner = Banner.objects.create(title="Original banner", image="banner.png", visible=True)
        shortcut = HomepageShortcut.objects.create(service=self.service, label="Original shortcut")
        award = Award.objects.create(title="Original award", image_url="https://example.test/award.png")
        video = HomepageVideo.objects.create(title="Original video", youtube_url="https://youtu.be/ZBcjm8dh1T4", poster_alt="Existing alternative text")
        cases = [
            ("create_update_service", "service_id", self.service, {"title": "Edited service", "description": "Details", "schedules": "Daily", "visible": "on"}, "title"),
            ("create_update_team_lead", "team_lead_id", self.lead, {"fullname": "Edited lead", "title": "Nurse", "bio": "Biography", "linkedin": "", "visible": "on"}, "fullname"),
            ("create_update_banner", "banner_id", banner, {"title": "Edited banner", "eyebrow": "", "description": "", "position": 0, "button_label": "Explore our services", "visible": "on"}, "title"),
            ("create_update_homepage_shortcut", "shortcut_id", shortcut, {"service": self.service.pk, "label": "Edited shortcut", "description": "", "icon": "heart-pulse", "accent": "sky", "ribbon_text": "", "ribbon_style": "sky", "ribbon_position": "right", "position": 0, "visible": "on"}, "label"),
            ("create_update_award", "award_id", award, {"title": "Edited award", "issuer": "", "year": "", "description": "", "image_url": "https://example.test/award.png", "position": 0, "visible": "on"}, "title"),
            ("create_update_homepage_video", "homepage_video_id", video, {"eyebrow": "Inside Sinel", "title": "Edited video", "description": "", "youtube_url": "https://youtu.be/ZBcjm8dh1T4", "poster_url": "", "visible": "on"}, "title"),
            ("create_update_album", "album_id", self.album, {"name": "Edited album"}, "name"),
        ]
        for route, identifier, instance, data, field in cases:
            with self.subTest(editor=route):
                url = reverse(f"dashboard:{route}")
                editor = self.client.get(url, {identifier: instance.pk})
                self.assertEqual(editor.status_code, 200)
                token = editor.context["editor_revision"]
                self.assertContains(editor, f'name="editor_revision" value="{token}"')
                payload = {**data, identifier: instance.pk, "editor_revision": token}
                result = self.client.post(url, payload)
                self.assertEqual(result.status_code, 302, getattr(result.context and result.context["form"], "errors", ""))
                response = self.client.post(url, {**payload, field: "Rejected stale overwrite"})
                self.assertEqual(response.status_code, 409)
                self.assertContains(response, "Open latest saved version", status_code=409)
                self.assertEqual(response.context["editor_revision"], token)
                instance.refresh_from_db()
                self.assertEqual(getattr(instance, field), data[field])
        video.refresh_from_db()
        self.assertEqual(video.poster_alt, "Existing alternative text")

    def test_editor_saves_do_not_overwrite_concurrent_curation_or_accept_mass_assignment(self):
        for kind, instance, data, _ in self.cases():
            if kind not in {"partner", "media", "page"}:
                continue
            with self.subTest(editor=kind):
                url = reverse(f"dashboard:create_update_{kind}")
                token = self.client.get(url, {f"{kind}_id": instance.pk}).context["editor_revision"]
                if kind == "page":
                    changes = {"menu_label": "Navigation title", "menu_position": 7}
                    forged = {"menu_label": "Forged navigation title", "menu_position": 2}
                else:
                    changes = {"featured": True, "featured_position": 7}
                    forged = {"featured": "", "featured_position": 2}
                type(instance).objects.filter(pk=instance.pk).update(**changes)
                self.assertEqual(self.edit(kind, {**data, **forged}, instance, token=token).status_code, 302)
                instance.refresh_from_db()
                for field, value in changes.items():
                    self.assertEqual(getattr(instance, field), value)

    def test_anonymous_and_auditor_cannot_submit_content_editor_changes(self):
        url = reverse("dashboard:create_update_partner")
        self.client.logout()
        self.assertEqual(self.client.post(url, self.partner_payload()).status_code, 302)
        self.client.force_login(self.user("auditor", Administrator.Role.AUDITOR))
        editor = self.client.get(url, {"partner_id": self.partner.pk})
        self.assertEqual(editor.status_code, 200)
        response = self.client.post(url, {**self.partner_payload(), "partner_id": self.partner.pk, "editor_revision": editor.context["editor_revision"]})
        self.assertEqual(response.status_code, 403)
        self.partner.refresh_from_db()
        self.assertEqual(self.partner.name, "Fictional partner")

    def test_failed_replacement_storage_keeps_database_and_existing_file(self):
        storage = Partner._meta.get_field("logo").storage
        existing_bytes = self.image_upload().read()
        self.partner.logo.name = storage.save("existing-logo.png", ContentFile(existing_bytes))
        self.partner.save(update_fields=["logo"])
        before = Partner.objects.filter(pk=self.partner.pk).values().get()
        old_name = self.partner.logo.name
        data = {**self.partner_payload(), "logo": self.image_upload()}
        with patch.object(storage, "save", side_effect=OSError("Fictional storage unavailable")), patch.object(storage, "delete") as delete:
            response = self.edit("partner", data, self.partner)
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "No content changes were saved", status_code=503)
        self.assertContains(response, "Select the replacement again", status_code=503)
        self.assertEqual(response.context["form"]["name"].value(), data["name"])
        self.assertEqual(response.context["partner"].logo.name, old_name)
        self.assertEqual(response.context["form"]["logo"].initial.name, old_name)
        self.assertEqual(Partner.objects.filter(pk=self.partner.pk).values().get(), before)
        delete.assert_not_called()
        self.assertTrue(storage.exists(old_name))
        with storage.open(old_name, "rb") as existing:
            self.assertEqual(existing.read(), existing_bytes)

    def test_invalid_replacement_keeps_durable_asset_in_context(self):
        response = self.edit("partner", {**self.partner_payload(), "name": "", "logo": self.image_upload()}, self.partner)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.context["partner"].logo.name, "partner.png")
        self.assertEqual(response.context["form"]["logo"].initial.name, "partner.png")

    def test_editor_help_and_error_descriptions_exist_without_javascript(self):
        response = self.client.get(reverse("dashboard:contact"))
        self.assertContains(response, 'id="id_lat_lng_helptext"')
        self.assertContains(response, 'aria-describedby="id_lat_lng_helptext"')
        response = self.edit("contact", {"email": "hello@example.test", "address": "Hospital", "telephone": "+233201234567", "lat_lng": "invalid"})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'id="id_lat_lng_error"', status_code=400)
        self.assertContains(response, 'aria-describedby="id_lat_lng_helptext id_lat_lng_error"', status_code=400)
        self.assertEqual(response.content.decode().count('id="id_lat_lng_error"'), 1)
