"""Manager API and legacy public-destination regressions with fictional records."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Administrator
from website.models import Award, Banner, HomepageVideo, Notification, Partner, SocialMediaLink, TeamLead


class EditorialManagerApiTests(TestCase):
    paths = ("/api/v1/team_leads", "/api/v1/social_media_links")

    def setUp(self):
        self.manager = self.user("manager")
        self.team = TeamLead.objects.create(
            fullname="Fictional API team member", title="Fictional specialist", bio="Fictional biography",
            photo="uploads/images/fictional-api-portrait.jpg", visible=False,
        )
        self.social = SocialMediaLink.objects.create(
            name="Fictional organization profile", image="uploads/images/fictional-api-social.png",
            link="https://example.test/fictional-profile",
        )
        self.api = APIClient()

    def user(self, label, **overrides):
        fields = {
            "email_address": f"api-{label}@example.test", "password": None,
            "fullname": f"Fictional API {label}", "is_staff": True, "is_active": True,
            "role": Administrator.Role.CONTENT_MANAGER,
        }
        fields.update(overrides)
        return Administrator.objects.create_user(**fields)

    def test_team_read_returns_photo_and_compatible_image_alias(self):
        self.api.force_authenticate(user=self.manager)
        response = self.api.get(self.paths[0])
        self.assertEqual(response.status_code, 200)
        record = next(row for row in response.json()["team_leads"] if row["id"] == self.team.pk)
        self.assertEqual(record["fullname"], self.team.fullname)
        self.assertEqual(record["image"], "http://testserver" + self.team.photo.url)
        self.assertEqual(record["photo"], record["image"])
        self.assertFalse(record["visible"])
        self.assertFalse(record["featured"])

    def test_missing_photo_uses_empty_backward_compatible_alias_without_crash(self):
        TeamLead.objects.filter(pk=self.team.pk).update(photo="")
        self.api.force_authenticate(user=self.manager)
        response = self.api.get(self.paths[0])
        self.assertEqual(response.status_code, 200)
        record = next(row for row in response.json()["team_leads"] if row["id"] == self.team.pk)
        self.assertEqual(record["image"], "")

    def test_social_link_read_uses_actual_model_and_absolute_image(self):
        self.api.force_authenticate(user=self.manager)
        response = self.api.get(self.paths[1])
        self.assertEqual(response.status_code, 200)
        record = response.json()["social_media_links"][0]
        self.assertEqual(record["id"], self.social.pk)
        self.assertEqual(record["name"], self.social.name)
        self.assertEqual(record["link"], self.social.link)
        self.assertEqual(record["image"], "http://testserver" + self.social.image.url)

    def test_anonymous_and_wrong_role_reads_and_mutations_remain_denied(self):
        for path in self.paths:
            with self.subTest(path=path, actor="anonymous"):
                self.assertEqual(self.api.get(path).status_code, 401)
                self.assertEqual(self.api.patch(path, {"id": self.team.pk, "fullname": "Injected"}).status_code, 401)
        for label, overrides in (
            ("front-desk", {"role": Administrator.Role.FRONT_DESK}),
            ("auditor", {"role": Administrator.Role.AUDITOR}),
            ("inactive", {"is_active": False}),
            ("nonstaff", {"is_staff": False}),
        ):
            self.api.force_authenticate(user=self.user(label, **overrides))
            for path in self.paths:
                with self.subTest(path=path, actor=label):
                    self.assertEqual(self.api.get(path).status_code, 403)
                    self.assertEqual(self.api.patch(path, {"id": self.team.pk, "fullname": "Injected"}).status_code, 403)
        self.team.refresh_from_db()
        self.assertEqual(self.team.fullname, "Fictional API team member")
        self.assertEqual(TeamLead.objects.count(), 1)
        self.assertEqual(SocialMediaLink.objects.count(), 1)


class LegacyPublicDestinationTests(TestCase):
    def setUp(self):
        self.partner = Partner.objects.create(
            name="Fictional destination partner", category="Corporate Partners", logo="fake/partner.png", visible=True,
        )
        self.banner = Banner.objects.create(title="Fictional destination banner", image="", visible=True)
        self.team = TeamLead.objects.create(
            fullname="Fictional destination member", title="Fictional care", bio="Biography", photo="fake/team.jpg", visible=True,
        )
        self.award = Award.objects.create(title="Fictional destination award", image="", image_url="https://example.test/fake-award.png", visible=True)
        self.video = HomepageVideo.objects.create(title="Fictional destination film", youtube_url="https://youtu.be/AbCdEf12345", visible=True)
        now = timezone.now()
        self.notice = Notification.objects.create(
            title="Fictional destination notice", message="Fictional hospital information",
            available_at=now - timedelta(hours=1), expires_at=now + timedelta(hours=1),
        )

    def update_destinations(self, value):
        for model, record, field in (
            (Partner, self.partner, "website"), (Banner, self.banner, "url"),
            (TeamLead, self.team, "linkedin"), (Award, self.award, "image_url"),
            (Notification, self.notice, "url"),
        ):
            model.objects.filter(pk=record.pk).update(**{field: value})
            record.refresh_from_db()

    def test_unsafe_stored_links_never_become_public_click_or_image_destinations(self):
        for unsafe in (
            "javascript:alert(123456)", "ftp://example.test/legacy-unsafe", "//example.test/legacy-unsafe",
            "https://example.test/legacy\nunsafe",
            "https://" + "user:secret@example.test/legacy-unsafe",  # Synthetic unsafe userinfo.
        ):
            with self.subTest(value=unsafe):
                self.update_destinations(unsafe)
                self.assertEqual(self.partner.public_website, "")
                self.assertEqual(self.notice.public_url, "")
                self.assertEqual(self.team.public_linkedin_url, "")
                self.assertEqual(self.award.display_image_url, "")
                self.assertEqual(self.banner.button_url, reverse("website:services"))
                for route in ("website:index", "website:partners", "website:doctors", "website:about"):
                    response = self.client.get(reverse(route))
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, unsafe)

    def test_stored_video_requires_http_scheme_even_when_host_and_id_look_valid(self):
        for unsafe in (
            "javascript://youtu.be/AbCdEf12345", "ftp://youtu.be/AbCdEf12345",
            "//youtu.be/AbCdEf12345",
            "https://" + "user:secret@youtu.be/AbCdEf12345",  # Synthetic unsafe userinfo.
        ):
            with self.subTest(value=unsafe):
                HomepageVideo.objects.filter(pk=self.video.pk).update(youtube_url=unsafe)
                self.video.refresh_from_db()
                self.assertEqual(self.video.youtube_id, "")
                self.assertEqual(self.video.embed_url, "")
                response = self.client.get(reverse("website:index"))
                self.assertNotContains(response, unsafe)
                self.assertNotContains(response, 'id="home-video-title"')

    def test_stored_unsafe_video_poster_uses_safe_provider_thumbnail(self):
        for unsafe in ("javascript:alert(123456)", "//example.test/legacy-poster", "ftp://example.test/legacy-poster"):
            HomepageVideo.objects.filter(pk=self.video.pk).update(poster_url=unsafe)
            self.video.refresh_from_db()
            self.assertEqual(self.video.display_poster_url, "https://i.ytimg.com/vi/AbCdEf12345/hqdefault.jpg")
            response = self.client.get(reverse("website:index"))
            self.assertNotContains(response, unsafe)

    def test_normal_http_and_https_destinations_are_preserved(self):
        for scheme in ("http", "https"):
            value = f"{scheme}://example.test/fictional-valid"
            self.update_destinations(value)
            self.assertEqual(self.partner.public_website, value)
            self.assertEqual(self.notice.public_url, value)
            self.assertEqual(self.banner.button_url, value)
            self.assertEqual(self.award.display_image_url, value)
            TeamLead.objects.filter(pk=self.team.pk).update(linkedin=f"{scheme}://www.linkedin.com/in/fictional-person/")
            self.team.refresh_from_db()
            self.assertEqual(self.team.public_linkedin_url, f"{scheme}://www.linkedin.com/in/fictional-person/")
            HomepageVideo.objects.filter(pk=self.video.pk).update(youtube_url=f"{scheme}://youtu.be/AbCdEf12345")
            self.video.refresh_from_db()
            self.assertEqual(self.video.youtube_id, "AbCdEf12345")
