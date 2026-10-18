from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from accounts.models import Administrator
from blog.forms import PageForm
from blog.models import Page
from dashboard.curation import GalleryPlacementForm, PagePlacementForm, PartnerPlacementForm, TeamPlacementForm
from dashboard.editor_state import TOKEN_FIELD, revision_token
from website.forms import HomepageVideoForm, MediaForm, PartnerForm, TeamLeadForm
from website.models import About, Album, HomepageVideo, Media, Partner, TeamLead
from website.page_content import PageMetadata


def editorial_user(label, role=Administrator.Role.CONTENT_MANAGER, active=True):
    return Administrator.objects.create_user(
        email_address=f"curation-{label}@example.test", password=None,
        fullname=f"Fictional {label}", is_staff=True, is_active=active, role=role,
    )


class CuratedPublicSelectionTests(TestCase):
    def member(self, name, **kwargs):
        return TeamLead.objects.create(
            fullname=name, title="Fictional department", bio="Fictional profile",
            photo="uploads/images/fictional-profile.jpg", visible=True, **kwargs,
        )

    def test_team_featured_order_capacity_and_hidden_removal(self):
        later = self.member("Fictional later", featured=True, featured_position=8)
        earlier = self.member("Fictional earlier", featured=True, featured_position=1)
        tied = self.member("Fictional tied", featured=True, featured_position=1)
        extra = self.member("Fictional extra", featured=True, featured_position=9)
        self.member("Fictional automatic")
        response = self.client.get(reverse("website:doctors"))
        self.assertEqual([row.pk for row in response.context["hero_members"]], [earlier.pk, tied.pk, later.pk])
        self.assertEqual(len(response.context["doctors"]), 5)
        earlier.visible = False
        earlier.save(update_fields=["visible"])
        response = self.client.get(reverse("website:doctors"))
        self.assertEqual([row.pk for row in response.context["hero_members"]], [tied.pk, later.pk, extra.pk])
        self.assertNotContains(response, "Fictional earlier")

    def test_team_no_eligible_selection_uses_existing_automatic_fallback(self):
        member = self.member("Fictional automatic")
        hidden = self.member("Fictional hidden", featured=True)
        hidden.visible = False
        hidden.save(update_fields=["visible"])
        response = self.client.get(reverse("website:doctors"))
        self.assertEqual([row.pk for row in response.context["hero_members"]], [member.pk])

    def test_partner_featured_selection_does_not_limit_directory_or_home_strip(self):
        partners = [Partner.objects.create(
            name=f"Fictional partner {index}", category="Corporate Partners",
            logo=f"uploads/images/fictional-partner-{index}.png", visible=True,
            featured=index > 0, featured_position=10 - index,
        ) for index in range(9)]
        response = self.client.get(reverse("website:partners"))
        self.assertEqual([row.pk for row in response.context["hero_partners"]], [row.pk for row in partners[:2:-1]])
        self.assertEqual(len(response.context["partners"]), 9)
        partners[8].visible = False
        partners[8].save(update_fields=["visible"])
        for route in ("website:partners", "website:index"):
            response = self.client.get(reverse(route))
            self.assertNotContains(response, "Fictional partner 8")
            self.assertContains(response, "Fictional partner 0")

    def test_partner_no_selection_retains_directory_order_fallback(self):
        last = Partner.objects.create(name="Fictional Zebra", logo="fake/zebra.png", category="Corporate Partners", visible=True)
        first = Partner.objects.create(name="Fictional Alpha", logo="fake/alpha.png", category="Corporate Partners", visible=True)
        response = self.client.get(reverse("website:partners"))
        self.assertEqual([row.pk for row in response.context["hero_partners"]], [first.pk, last.pk])

    def test_gallery_cover_metadata_and_hidden_selection_fallback(self):
        album = Album.objects.create(name="Fictional gallery")
        selected = Media.objects.create(
            album=album, name="Fictional selected", description="Fictional caption", file="fake/selected.jpg",
            visible=True, featured=True, alternative_text='Fictional photo "description"', credit="Fictional photographer",
        )
        newest = Media.objects.create(album=album, name="Fictional newest", description="New caption", file="fake/newest.jpg", visible=True)
        response = self.client.get(reverse("website:gallery"))
        self.assertEqual(response.context["featured"].pk, selected.pk)
        self.assertContains(response, f'alt="{escape(selected.alternative_text)}"')
        self.assertContains(response, selected.credit)
        selected.visible = False
        selected.save(update_fields=["visible"])
        response = self.client.get(reverse("website:gallery"))
        self.assertEqual(response.context["featured"].pk, newest.pk)
        self.assertNotContains(response, "Fictional photographer")


class PagePlacementAndMetadataTests(TestCase):
    def setUp(self):
        self.author = editorial_user("author")

    def page(self, title, **kwargs):
        return Page.objects.create(title=title, content="<p>Fictional public information.</p>", by=self.author, visible=True, **kwargs)

    def test_all_footer_links_beyond_five_are_explicitly_available_and_ordered(self):
        pages = [self.page(f"Fictional page {index}", menu_position=7 - index) for index in range(7)]
        response = self.client.get(reverse("website:index"))
        self.assertEqual([page.pk for page in response.context["request"].pages], [page.pk for page in reversed(pages)])
        for page in pages:
            self.assertContains(response, reverse("website:static_page_view", args=[page.pk, page.slug]))

    def test_header_footer_hidden_and_unlinked_page_policies(self):
        header = self.page("Fictional header-only", show_in_header=True, show_in_footer=False, menu_label="Visitor information")
        hidden = self.page("Fictional hidden page", show_in_header=True)
        hidden.visible = False
        hidden.save(update_fields=["visible"])
        unlinked = self.page("Fictional direct-only", show_in_header=False, show_in_footer=False)
        response = self.client.get(reverse("website:index"))
        self.assertEqual([row.pk for row in response.context["request"].header_pages], [header.pk])
        self.assertNotIn(header.pk, [row.pk for row in response.context["request"].pages])
        self.assertContains(response, "Visitor information")
        self.assertNotContains(response, "Fictional hidden page")
        self.assertNotContains(response, "Fictional direct-only")
        self.assertEqual(self.client.get(reverse("website:static_page_view", args=[unlinked.pk, unlinked.slug])).status_code, 200)
        self.assertEqual(self.client.get(reverse("website:static_page_view", args=[hidden.pk, hidden.slug])).status_code, 404)

    def test_metadata_is_escaped_in_title_and_social_attributes(self):
        title = '<script>alert("fictional-title")</script>'
        description = 'Fictional description " onload="alert(7)'
        PageMetadata.objects.create(key="home", title=title, description=description)
        response = self.client.get(reverse("website:index"))
        self.assertContains(response, f"<title>{escape(title)}</title>")
        self.assertContains(response, f'<meta property="og:description" content="{escape(description)}">')
        self.assertNotContains(response, title)


class CurationDashboardTests(TestCase):
    def setUp(self):
        self.manager = editorial_user("manager")
        self.member = TeamLead.objects.create(fullname="Fictional curator profile", title="Care team", bio="Biography", photo="fake/profile.jpg", visible=True)
        self.url = reverse("dashboard:curation_edit", args=["team", self.member.pk])
        self.client.force_login(self.manager)

    def payload(self, record=None, **kwargs):
        record = record or self.member
        result = {TOKEN_FIELD: revision_token(TeamLead, record, TeamPlacementForm.Meta.fields), "featured": "on", "featured_position": 4}
        result.update(kwargs)
        return result

    def test_save_display_settings_without_editing_profile_or_visibility(self):
        response = self.client.post(self.url, self.payload(fullname="Injected name", visible=""))
        self.assertRedirects(response, reverse("dashboard:curation", args=["team"]))
        self.member.refresh_from_db()
        self.assertTrue(self.member.featured)
        self.assertEqual(self.member.featured_position, 4)
        self.assertEqual(self.member.fullname, "Fictional curator profile")
        self.assertTrue(self.member.visible)
        payload = self.payload()
        payload.pop("featured")
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.member.refresh_from_db()
        self.assertFalse(self.member.featured)

    def test_stale_placement_cannot_overwrite_latest_and_keeps_attempted_values(self):
        payload = self.payload(featured_position=12)
        TeamLead.objects.filter(pk=self.member.pk).update(featured_position=6)
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'value="12"', status_code=409)
        self.member.refresh_from_db()
        self.assertEqual(self.member.featured_position, 6)

    def test_invalid_unsigned_and_oversized_position_do_not_mutate(self):
        response = self.client.post(self.url, self.payload(featured_position=10000))
        self.assertEqual(response.status_code, 400)
        self.member.refresh_from_db()
        self.assertFalse(self.member.featured)
        response = self.client.post(self.url, self.payload(**{TOKEN_FIELD: "tampered"}))
        self.assertEqual(response.status_code, 409)
        self.member.refresh_from_db()
        self.assertEqual(self.member.featured_position, 0)

    def test_unauthorized_readonly_and_revoked_users_cannot_save(self):
        self.client.logout()
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 302)
        for role in (Administrator.Role.FRONT_DESK, Administrator.Role.AUDITOR):
            user = editorial_user(role, role=role)
            self.client.force_login(user)
            self.assertEqual(self.client.post(self.url, self.payload()).status_code, 403)
        auditor = Administrator.objects.get(email_address="curation-auditor@example.test")
        self.client.force_login(auditor)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        revoked = editorial_user("revoked", active=False)
        self.client.force_login(revoked)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 302)
        self.member.refresh_from_db()
        self.assertFalse(self.member.featured)

    def test_unknown_group_and_missing_records_have_controlled_not_found(self):
        self.assertEqual(self.client.get(reverse("dashboard:curation", args=["unsupported"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("dashboard:curation_edit", args=["team", 999999])).status_code, 404)

    def test_form_field_ownership_keeps_legacy_editors_from_clearing_curation(self):
        contracts = (
            (TeamLeadForm, TeamPlacementForm), (PartnerForm, PartnerPlacementForm),
            (MediaForm, GalleryPlacementForm), (PageForm, PagePlacementForm),
        )
        for ordinary, placement in contracts:
            with self.subTest(form=ordinary.__name__):
                self.assertFalse(set(ordinary().fields) & set(placement().fields))


class HomepageVideoContentTests(TestCase):
    def setUp(self):
        self.video = HomepageVideo.objects.create(
            title="Fictional new hospital film", youtube_url="https://youtu.be/AbCdEf12345",
            poster_url="https://example.test/fictional-video.jpg", poster_alt="Fictional film poster",
            duration_label="2:15 introduction", link_label="Watch our introduction", visible=True,
        )

    def test_public_video_uses_editable_metadata_and_canonical_about_facts(self):
        About.objects.create(years_value="42+", years_label="Years of specialist care", availability_value="Daily", availability_label="Visiting availability")
        response = self.client.get(reverse("website:index"))
        for value in ("42+", "Years of specialist care", "Daily", "Visiting availability", "2:15 introduction", "Watch our introduction"):
            self.assertContains(response, value)
        self.assertContains(response, 'alt="Fictional film poster"')
        self.assertNotContains(response, "1:36 hospital tour")

    def test_omitted_legacy_metadata_is_preserved_and_explicit_blank_is_clear(self):
        payload = {"eyebrow": "Inside", "title": "Updated fictional film", "description": "Fictional care", "youtube_url": self.video.youtube_url, "poster_url": self.video.poster_url, "visible": True}
        form = HomepageVideoForm(payload, instance=self.video)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.video.refresh_from_db()
        self.assertEqual(self.video.duration_label, "2:15 introduction")
        self.assertEqual(self.video.poster_alt, "Fictional film poster")
        form = HomepageVideoForm({**payload, "duration_label": "", "poster_alt": ""}, instance=self.video)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        response = self.client.get(reverse("website:index"))
        self.assertNotContains(response, "home-video-duration")
        self.assertContains(response, 'alt="Updated fictional film"')

    def test_video_metadata_bounds_and_unsafe_destination_are_rejected(self):
        payload = {"eyebrow": "Inside", "title": "Fictional film", "youtube_url": self.video.youtube_url, "poster_url": self.video.poster_url, "visible": True}
        for name, value in (("duration_label", "x" * 41), ("poster_alt", "x" * 181), ("description", "x" * 421), ("poster_url", "javascript:alert(1)")):
            with self.subTest(field=name):
                form = HomepageVideoForm({**payload, name: value}, instance=self.video)
                self.assertFalse(form.is_valid())
                self.assertIn(name, form.errors)
