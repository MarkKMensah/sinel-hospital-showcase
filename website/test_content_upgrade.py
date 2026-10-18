"""Populate the previous schema with fictional records before the CMS upgrade."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class EditorialContentUpgradeTests(TransactionTestCase):
    migrate_from = [
        ("website", "0022_about_intro_and_optional_team_lead"),
        ("blog", "0006_page_slug"),
        ("accounts", "0005_restore_legacy_administrator_staff_access"),
    ]
    migrate_to = [
        ("website", "0023_editorial_content_controls"),
        ("blog", "0007_editorial_content_controls"),
        ("accounts", "0005_restore_legacy_administrator_staff_access"),
    ]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        executor.migrate(self.migrate_from)
        self.old_apps = executor.loader.project_state(self.migrate_from).apps
        self.snapshots = []

    def tearDown(self):
        try:
            MigrationExecutor(connection).migrate(self.latest_targets)
        finally:
            super().tearDown()

    def remember(self, app_label, model_name, **fields):
        model = self.old_apps.get_model(app_label, model_name)
        record = model.objects.create(**fields)
        self.snapshots.append((app_label, model_name, model.objects.values().get(pk=record.pk)))
        return record

    def test_populated_content_ids_dates_files_authors_and_relationships_survive(self):
        author = self.remember(
            "accounts", "Administrator", email_address="migration-editor@example.test",
            fullname="Fictional migration editor", role="content_manager", is_staff=True,
            is_active=True, password="!unusable-fictional-password",
        )
        about = self.remember(
            "website", "About", overview="<p>Fictional retained overview.</p>",
            mission="<p>Fictional mission.</p>", vision="<p>Fictional vision.</p>",
            value="<p>Fictional values.</p>", hero_title="Fictional existing introduction",
            hero_description="Fictional existing supporting text.", years_value="43+",
            years_label="Fictional years label", availability_value="Daily",
            availability_label="Fictional hours label", hero_note="Fictional established note.",
        )
        contact = self.remember(
            "website", "Contact", email="migration-care@example.test", telephone="+233201234567",
            address="42 Fictional Migration Road", gps="EX-000-0000", lat_lng="5.6,-0.01",
        )
        visible_lead = self.remember(
            "website", "TeamLead", fullname="Fictional visible lead", title="Fictional team",
            bio="Existing fictional biography", photo="uploads/images/fictional-migration-visible.jpg",
            linkedin="https://www.linkedin.com/in/fictional-migration-profile/", visible=True,
        )
        hidden_lead = self.remember(
            "website", "TeamLead", fullname="Fictional hidden lead", title="Fictional team",
            bio="Retained hidden biography", photo="uploads/images/fictional-migration-hidden.jpg", visible=False,
        )
        service = self.remember(
            "website", "Service", title="Fictional established service",
            description="<p>Retained service description.</p>", schedules="<p>Retained schedule.</p>",
            image="uploads/images/fictional-migration-service.jpg", visible=True,
        )
        service.doctors.set([visible_lead, hidden_lead])
        empty_service = self.remember(
            "website", "Service", title="Fictional unassigned service",
            description="<p>No assignment required.</p>", schedules="",
            image="uploads/images/fictional-migration-unassigned.jpg", visible=False,
        )
        testimonial = self.remember(
            "website", "Testimonial", username="Fictional family", message="A retained fictional account.",
            service=service, doctor=hidden_lead, photo="uploads/images/fictional-migration-quote.jpg", visible=True,
        )
        partner = self.remember(
            "website", "Partner", name="Fictional existing partner", category="Financial Partnerss",
            description="Retained partner description", website="https://example.test/retained-partner",
            logo="uploads/images/fictional-migration-partner.png", visible=True,
        )
        album = self.remember("website", "Album", name="Fictional existing album")
        image = self.remember(
            "website", "Media", album=album, name="Fictional existing photograph",
            description="Retained photograph caption", file="uploads/images/fictional-migration-gallery.jpg",
            visible=True, media_type="image",
        )
        video = self.remember(
            "website", "HomepageVideo", title="Fictional existing video", eyebrow="Existing film",
            description="Retained video introduction", youtube_url="https://youtu.be/AbCdEf12345",
            poster="uploads/videos/fictional-migration-poster.jpg",
            poster_url="https://example.test/retained-video.jpg", visible=True,
        )
        shortcut = self.remember(
            "website", "HomepageShortcut", service=service, label="Fictional shortcut",
            description="Retained shortcut description", position=3, visible=True,
            ribbon_text="Featured", ribbon_style="sky", ribbon_position="right",
        )
        page = self.remember(
            "blog", "Page", title="Fictional existing public page", slug="retained-existing-slug",
            content="<p>Retained page content.</p>", by=author, visible=True,
        )
        post = self.remember(
            "blog", "Post", title="Fictional existing news", content="<p>Retained article content.</p>",
            by=author, tags="fictional, migration", thumbnail="uploads/images/fictional-migration-post.jpg", visible=True,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        migrated_apps = executor.loader.project_state(self.migrate_to).apps
        for app_label, model_name, original in self.snapshots:
            with self.subTest(model=model_name, identifier=original["id"]):
                migrated = migrated_apps.get_model(app_label, model_name).objects.values().get(pk=original["id"])
                for name, value in original.items():
                    self.assertEqual(migrated[name], value, f"Changed legacy field {model_name}.{name}")

        migrated_service = migrated_apps.get_model("website", "Service").objects.get(pk=service.pk)
        self.assertEqual(
            list(migrated_service.doctors.order_by("pk").values_list("pk", flat=True)),
            sorted([visible_lead.pk, hidden_lead.pk]),
        )
        self.assertFalse(migrated_apps.get_model("website", "Service").objects.get(pk=empty_service.pk).doctors.exists())
        for model_name, record in (("TeamLead", visible_lead), ("Partner", partner), ("Media", image)):
            migrated = migrated_apps.get_model("website", model_name).objects.get(pk=record.pk)
            self.assertFalse(migrated.featured)
            self.assertEqual(migrated.featured_position, 0)
        migrated_page = migrated_apps.get_model("blog", "Page").objects.get(pk=page.pk)
        self.assertFalse(migrated_page.show_in_header)
        self.assertTrue(migrated_page.show_in_footer)
        self.assertEqual(migrated_page.menu_label, "")
        migrated_video = migrated_apps.get_model("website", "HomepageVideo").objects.get(pk=video.pk)
        self.assertEqual(migrated_video.poster_alt, "")
        self.assertEqual(migrated_video.duration_label, "")
        self.assertEqual(migrated_video.link_label, "Watch the hospital tour")
        self.assertEqual(migrated_apps.get_model("website", "SiteSettings").objects.count(), 0)
        self.assertEqual(migrated_apps.get_model("website", "PageSection").objects.count(), 0)
        self.assertEqual(migrated_apps.get_model("website", "PageMetadata").objects.count(), 0)
        # Keep these references explicit: their metadata was also included above.
        self.assertTrue(all(record.pk for record in (about, contact, testimonial, shortcut, post)))
