from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import reverse
from django.test import TestCase

from .models import (
    Album,
    Award,
    Banner,
    HomepageShortcut,
    HomepageVideo,
    Media,
    Partner,
    Service,
    TeamLead,
    Testimonial,
)


class TestViews(TestCase):

    def test_index_view_renders(self):
        url = reverse("website:index")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "website/index.html")
        self.assertContains(resp, "Better Healthcare")

    def test_public_layout_includes_persistent_contact_actions(self):
        response = self.client.get(reverse("website:index"))

        self.assertContains(response, 'class="mobile-contact-dock"')
        self.assertContains(response, "mobile-contact-action--whatsapp")
        self.assertContains(response, "desktop-contact-actions")
        self.assertContains(response, "header-contact-button--whatsapp")

    def test_services_menu_is_polished_sorted_and_visibility_aware(self):
        Service.objects.create(
            title="Zebra Care",
            description="<p>Published care.</p>",
            schedules="<p>Every day</p>",
            image="uploads/images/zebra-care.jpg",
            visible=True,
        )
        Service.objects.create(
            title="Antenatal Care",
            description="<p>Published care.</p>",
            schedules="<p>Weekdays</p>",
            image="uploads/images/antenatal-care.jpg",
            visible=True,
        )
        Service.objects.create(
            title="Internal Draft Service",
            description="<p>Not published.</p>",
            schedules="<p>Unavailable</p>",
            image="uploads/images/internal-draft.jpg",
            visible=False,
        )

        response = self.client.get(reverse("website:index"))
        content = response.content.decode()

        self.assertContains(response, 'class="services-mega-menu"')
        self.assertContains(response, "Find the right service")
        self.assertContains(response, "View all services")
        self.assertContains(response, "Antenatal Care")
        self.assertContains(response, "Zebra Care")
        self.assertNotContains(response, "Internal Draft Service")
        self.assertLess(content.index("Antenatal Care"), content.index("Zebra Care"))

    def test_homepage_uses_first_visible_banner_and_ordered_shortcuts(self):
        service = Service.objects.create(
            title="Primary Care",
            description="<p>Care for everyday health needs.</p>",
            schedules="<p>Every day</p>",
            image="uploads/images/primary-care.jpg",
            visible=True,
        )
        later_service = Service.objects.create(
            title="Pharmacy",
            description="<p>Medicine support day and night.</p>",
            schedules="<p>Always open</p>",
            image="uploads/images/pharmacy.jpg",
            visible=True,
        )
        Banner.objects.create(
            title="Later banner",
            image="uploads/images/later.jpg",
            position=20,
            visible=True,
        )
        Banner.objects.create(
            title="Care close to home",
            description="Trusted family healthcare in Tema.",
            button_label="See primary care",
            service=service,
            image="uploads/images/first.jpg",
            position=10,
            visible=True,
        )
        HomepageShortcut.objects.create(
            service=later_service,
            label="24 Hour Pharmacy",
            position=20,
            visible=True,
        )
        HomepageShortcut.objects.create(
            service=service,
            label="General Medicine",
            position=10,
            visible=True,
        )

        response = self.client.get(reverse("website:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Care close to home")
        self.assertNotContains(response, "Later banner")
        self.assertContains(response, "See primary care")
        content = response.content.decode()
        self.assertLess(
            content.index("General Medicine"),
            content.index("24 Hour Pharmacy"),
        )

    def test_homepage_hides_shortcuts_for_hidden_services(self):
        hidden_service = Service.objects.create(
            title="Hidden Service",
            description="<p>Not ready for publication.</p>",
            schedules="<p>Unavailable</p>",
            image="uploads/images/hidden.jpg",
            visible=False,
        )
        HomepageShortcut.objects.create(
            service=hidden_service,
            label="Should not appear",
            visible=True,
        )

        response = self.client.get(reverse("website:index"))

        self.assertNotContains(response, "Should not appear")

    def test_homepage_shortcut_ribbon_is_optional_and_dashboard_managed(self):
        service = Service.objects.create(
            title="New Family Service",
            description="<p>Care for the whole family.</p>",
            schedules="<p>Weekdays</p>",
            image="uploads/images/new-family-service.jpg",
            visible=True,
        )
        HomepageShortcut.objects.create(
            service=service,
            label="Family Care",
            ribbon_text="New",
            ribbon_style=HomepageShortcut.RibbonStyle.RED,
            ribbon_position=HomepageShortcut.RibbonPosition.LEFT,
            visible=True,
        )

        response = self.client.get(reverse("website:index"))

        self.assertContains(response, "home-shortcut-ribbon-left")
        self.assertContains(response, "home-shortcut-ribbon-red")
        self.assertContains(
            response,
            (
                '<span class="home-shortcut-ribbon '
                'home-shortcut-ribbon-left '
                'home-shortcut-ribbon-red">New</span>'
            ),
            html=True,
        )

    def test_hidden_service_detail_returns_not_found(self):
        hidden_service = Service.objects.create(
            title="Hidden Service",
            description="<p>Not ready for publication.</p>",
            schedules="<p>Unavailable</p>",
            image="uploads/images/hidden.jpg",
            visible=False,
        )

        response = self.client.get(
            reverse(
                "website:service_details",
                args=[hidden_service.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_about_view_renders(self):
        url = reverse("website:about")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "website/about.html")
        self.assertContains(resp, "About Us")
        self.assertContains(resp, "Care that has grown with generations")

    def test_about_awards_follow_visible_dashboard_records(self):
        Award.objects.all().delete()
        visible_award = Award.objects.create(
            title="Clinical Excellence Recognition",
            issuer="Healthcare Council",
            year=2026,
            image_url="https://example.com/visible-award.jpg",
            position=10,
            visible=True,
        )
        Award.objects.create(
            title="Unpublished Recognition",
            image_url="https://example.com/hidden-award.jpg",
            position=20,
            visible=False,
        )

        response = self.client.get(reverse("website:about"))

        self.assertContains(response, "Awards & Achievements")
        self.assertContains(response, "Clinical Excellence Recognition")
        self.assertContains(response, "Healthcare Council · 2026")
        self.assertNotContains(response, "Unpublished Recognition")
        self.assertContains(response, "recognition-lightbox")

        visible_award.delete()
        refreshed_response = self.client.get(reverse("website:about"))

        self.assertNotContains(refreshed_response, "recognition-section")

    def test_seed_style_award_title_is_neutral_on_public_page(self):
        award = Award(
            title="Sinel Hospital recognition 3",
            image_url="https://example.com/award.jpg",
        )

        self.assertEqual(award.public_title, "Award & Achievement")

    def test_homepage_video_uses_click_to_play_embed(self):
        HomepageVideo.objects.all().delete()
        video = HomepageVideo.objects.create(
            eyebrow="Inside Sinel",
            title="The New Sinel",
            description="See the hospital and the people behind your care.",
            youtube_url="https://youtu.be/ZBcjm8dh1T4",
            poster_url="https://example.com/poster.jpg",
            visible=True,
        )
        Service.objects.create(
            title="Visible Service",
            description="<p>Available.</p>",
            schedules="<p>Every day</p>",
            image="uploads/images/service.jpg",
            visible=True,
        )
        Service.objects.create(
            title="Hidden Service",
            description="<p>Not ready.</p>",
            schedules="<p>Unavailable</p>",
            image="uploads/images/hidden-service.jpg",
            visible=False,
        )

        response = self.client.get(reverse("website:index"))

        self.assertContains(response, "The New Sinel")
        self.assertContains(response, "<span>Services</span>", html=True)
        self.assertNotContains(response, "Published services")
        self.assertContains(
            response,
            "https://www.youtube.com/embed/ZBcjm8dh1T4",
        )
        self.assertContains(response, "data-video-trigger")
        self.assertNotContains(
            response,
            'iframe src="https://www.youtube',
        )
        self.assertEqual(response.context["visible_service_count"], 1)
        self.assertEqual(video.youtube_id, "ZBcjm8dh1T4")

    def test_homepage_video_rejects_non_youtube_urls(self):
        video = HomepageVideo(
            title="Untrusted video",
            youtube_url="https://example.com/video",
        )

        with self.assertRaises(ValidationError):
            video.full_clean()

    def test_contact_view_renders(self):
        url = reverse("website:contact")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "website/contact.html")
        self.assertContains(resp, "Care is close at hand")
        self.assertContains(resp, "Choose what works for you")

    def test_public_testimonials_follow_visible_dashboard_records(self):
        visible_testimonial = Testimonial.objects.create(
            username="Visible Patient",
            message="Sinel provided excellent care.",
            visible=True,
        )
        Testimonial.objects.create(
            username="Hidden Patient",
            message="This is not ready to publish.",
            visible=False,
        )

        response = self.client.get(reverse("website:index"))

        self.assertContains(response, "What they say about us")
        self.assertContains(response, "Visible Patient")
        self.assertNotContains(response, "Hidden Patient")
        self.assertContains(response, "data-testimonial-previous")
        self.assertContains(response, "data-testimonial-next")

        visible_testimonial.delete()
        refreshed_response = self.client.get(reverse("website:index"))

        self.assertNotContains(refreshed_response, "Visible Patient")

    def test_partners_are_synchronised_across_public_views(self):
        corporate_partner = Partner.objects.create(
            name="Visible Corporate Partner",
            logo="uploads/images/corporate-partner.jpg",
            description="Supporting employee wellbeing.",
            category="Corporate Partners",
            visible=True,
        )
        Partner.objects.create(
            name="Visible Insurance Partner",
            logo="uploads/images/insurance-partner.jpg",
            category="Insurance Partners",
            visible=True,
        )
        Partner.objects.create(
            name="Hidden Partner",
            logo="uploads/images/hidden-partner.jpg",
            category="Corporate Partners",
            visible=False,
        )

        homepage = self.client.get(reverse("website:index"))
        partner_page = self.client.get(reverse("website:partners"))

        self.assertContains(homepage, "partner-marquee")
        self.assertContains(homepage, "Visible Corporate Partner")
        self.assertNotContains(homepage, "Hidden Partner")
        self.assertContains(partner_page, "Better health happens together")
        self.assertContains(partner_page, "partner-card-grid")
        self.assertContains(partner_page, "Visible Corporate Partner")
        self.assertContains(partner_page, "Visible Insurance Partner")
        self.assertNotContains(partner_page, "Hidden Partner")
        self.assertEqual(
            partner_page.context["categories"],
            ["Corporate Partners", "Insurance Partners"],
        )

        corporate_partner.delete()

        refreshed_homepage = self.client.get(reverse("website:index"))
        refreshed_partner_page = self.client.get(reverse("website:partners"))

        self.assertNotContains(
            refreshed_homepage,
            "Visible Corporate Partner",
        )
        self.assertNotContains(
            refreshed_partner_page,
            "Visible Corporate Partner",
        )

    def test_gallery_view_renders(self):
        url = reverse("website:gallery")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "website/gallery.html")
        self.assertContains(resp, "Our Gallery")
        self.assertContains(resp, "Inside Sinel")
        self.assertContains(resp, "gallery-collection")
        self.assertNotContains(resp, "/static/css/main.css")

    def test_gallery_renders_only_visible_media_as_cards(self):
        album = Album.objects.create(name="Hospital")
        Media.objects.create(
            name="Care Team",
            description="Meet the Sinel care team.",
            album=album,
            file="uploads/images/care-team.jpg",
            visible=True,
        )
        Media.objects.create(
            name="Draft Image",
            description="Not ready for publication.",
            album=album,
            file="uploads/images/draft.jpg",
            visible=False,
        )

        response = self.client.get(reverse("website:gallery"))

        self.assertContains(response, "gallery-grid")
        self.assertContains(response, "Care Team")
        self.assertNotContains(response, "Draft Image")

    def test_team_page_renders_visible_members_in_ordered_directory(self):
        TeamLead.objects.create(
            fullname="Nurse Ama",
            bio="Experienced nurse and midwife.",
            title="Nursing Team",
            photo="uploads/images/nurse-ama.jpg",
            visible=True,
        )
        TeamLead.objects.create(
            fullname="Dr. Kofi",
            bio="Clinical dietician.",
            title="Dietician",
            photo="uploads/images/dr-kofi.jpg",
            visible=True,
        )
        TeamLead.objects.create(
            fullname="Dr. Michael McCarthy",
            bio="Chief Executive Officer.",
            title="Medical Team",
            photo="uploads/images/dr-mccarthy.jpg",
            visible=True,
        )
        TeamLead.objects.create(
            fullname="Hidden Person",
            bio="Not ready for publication.",
            title="Administration",
            photo="uploads/images/hidden-person.jpg",
            visible=False,
        )

        response = self.client.get(reverse("website:doctors"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "website/team.html")
        self.assertContains(response, "People behind your care")
        self.assertContains(response, "team-grid")
        self.assertContains(response, "Nurse Ama")
        self.assertContains(response, "Dr. Kofi")
        self.assertContains(response, "Team Members")
        self.assertNotContains(response, "Visible team member")
        self.assertNotContains(response, "Hidden Person")
        self.assertEqual(
            response.context["specialities"],
            ["Dietician", "Medical Team", "Nursing Team"],
        )
        self.assertEqual(
            [member.fullname for member in response.context["hero_members"]],
            ["Dr. Michael McCarthy", "Dr. Kofi", "Nurse Ama"],
        )

    def test_team_profile_display_helpers_reject_placeholder_content(self):
        member = TeamLead(
            fullname="Team Member",
            bio=".",
            title="Care Team",
            photo="uploads/images/team-member.jpg",
            linkedin="https://www.linkedin.com/feed",
        )

        self.assertEqual(member.display_bio, "")
        self.assertEqual(member.public_linkedin_url, "")

        member.bio = ".Dr. Team Member provides compassionate care."
        member.linkedin = "https://www.linkedin.com/in/team-member/"

        self.assertEqual(
            member.display_bio,
            "Dr. Team Member provides compassionate care.",
        )
        self.assertEqual(
            member.public_linkedin_url,
            "https://www.linkedin.com/in/team-member/",
        )

    def test_services_page_only_lists_visible_services(self):
        Service.objects.create(
            title="Published Service",
            description="<p>Available.</p>",
            schedules="<p>Every day</p>",
            image="uploads/images/published.jpg",
            visible=True,
        )
        Service.objects.create(
            title="Draft Service",
            description="<p>Not yet available.</p>",
            schedules="<p>Unavailable</p>",
            image="uploads/images/draft.jpg",
            visible=False,
        )

        response = self.client.get(reverse("website:services"))

        self.assertContains(response, "Published Service")
        self.assertNotContains(response, "Draft Service")

    def test_public_pages_use_native_interactions_without_legacy_plugins(self):
        homepage = self.client.get(reverse("website:index"))
        gallery = self.client.get(reverse("website:gallery"))

        self.assertContains(homepage, "testimonial_carousel.js")
        self.assertNotContains(homepage, "owl.carousel")
        self.assertNotContains(homepage, "jquery-3.5.1")
        self.assertNotContains(homepage, "wow.min.js")
        self.assertContains(homepage, "testimonial_carousel.js?v=20260729-3")
        self.assertContains(gallery, "gallery_lightbox.js")
        self.assertNotContains(gallery, "jquery.fancybox")
        self.assertNotContains(gallery, "jquery.flexslider")

    def test_testimonial_rotation_never_scrolls_the_page_viewport(self):
        script_path = (
            settings.BASE_DIR
            / "website"
            / "static"
            / "js"
            / "testimonial_carousel.js"
        )
        script = script_path.read_text(encoding="utf-8")

        self.assertNotIn("scrollIntoView", script)
        self.assertIn("carousel.scrollTo", script)
        self.assertIn("carousel.scrollBy", script)
