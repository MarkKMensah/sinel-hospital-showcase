from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class BannerCarouselContentMigrationTests(TransactionTestCase):
    migrate_from = [("website", "0020_homepageshortcut_ribbon")]
    migrate_to = [("website", "0021_banner_carousel_content")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        executor.migrate(self.migrate_from)
        historical_apps = executor.loader.project_state(self.migrate_from).apps
        Banner = historical_apps.get_model("website", "Banner")
        self.existing = []
        for position, description, visible in (
            (7, "", True),
            (2, None, False),
            (7, "Supporting text written by the hospital.", True),
        ):
            banner = Banner.objects.create(
                title=f"Existing banner {len(self.existing) + 1}",
                description=description,
                image=f"uploads/images/banner-{len(self.existing) + 1}.jpg",
                url="https://example.test/hospital-service",
                button_label="Explore our services",
                position=position,
                visible=visible,
            )
            self.existing.append(
                {
                    "id": banner.pk,
                    "title": banner.title,
                    "description": banner.description,
                    "image": str(banner.image),
                    "url": banner.url,
                    "button_label": banner.button_label,
                    "position": banner.position,
                    "visible": banner.visible,
                    "created_at": banner.created_at,
                    "updated_at": banner.updated_at,
                }
            )

    def tearDown(self):
        try:
            MigrationExecutor(connection).migrate(self.latest_targets)
        finally:
            super().tearDown()

    def test_existing_banners_keep_content_and_visibility_after_backfill(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        migrated_apps = executor.loader.project_state(self.migrate_to).apps
        Banner = migrated_apps.get_model("website", "Banner")
        expected_default = (
            "Trusted, compassionate care for every stage of life—from us to you."
        )

        self.assertEqual(Banner.objects.count(), len(self.existing))
        for original in self.existing:
            with self.subTest(banner_id=original["id"]):
                banner = Banner.objects.get(pk=original["id"])
                self.assertEqual(banner.eyebrow, "Specialist family care in Tema")
                self.assertEqual(
                    banner.description,
                    original["description"] or expected_default,
                )
                for field in (
                    "title",
                    "url",
                    "button_label",
                    "position",
                    "visible",
                    "created_at",
                    "updated_at",
                ):
                    self.assertEqual(getattr(banner, field), original[field])
                self.assertEqual(str(banner.image), original["image"])

        self.assertEqual(
            list(Banner.objects.values_list("id", flat=True)),
            [
                banner["id"]
                for banner in sorted(
                    self.existing,
                    key=lambda banner: (banner["position"], banner["id"]),
                )
            ],
        )
