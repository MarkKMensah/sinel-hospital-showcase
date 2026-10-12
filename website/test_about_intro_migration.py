from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from website.models import About as CurrentAbout


class AboutIntroductionMigrationTests(TransactionTestCase):
    migrate_from = [("website", "0021_banner_carousel_content")]
    migrate_to = [("website", "0022_about_intro_and_optional_team_lead")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.latest_targets = executor.loader.graph.leaf_nodes()
        executor.migrate(self.migrate_from)
        historical_apps = executor.loader.project_state(self.migrate_from).apps
        about_model = historical_apps.get_model("website", "About")
        service_model = historical_apps.get_model("website", "Service")
        team_model = historical_apps.get_model("website", "TeamLead")
        self.existing_about = []
        for copy in (
            {name: f"<h2>Existing {name}</h2>" for name in ("overview", "mission", "vision", "value")},
            dict.fromkeys(("overview", "mission", "vision", "value"), ""),
        ):
            record = about_model.objects.create(**copy)
            self.existing_about.append(about_model.objects.values().get(pk=record.pk))
        members = [
            team_model.objects.create(
                fullname=f"Existing specialist {index}",
                title="Hospital team",
                bio="Existing biography",
                photo=f"uploads/images/migration-team-{index}.jpg",
                visible=bool(index),
            )
            for index in range(2)
        ]
        self.service = service_model.objects.create(
            title="Existing clinic",
            description="<p>Existing care information</p>",
            schedules="<p>Existing schedule</p>",
            image="uploads/images/migration-service.jpg",
            visible=True,
        )
        self.service.doctors.set(members)
        self.member_ids = sorted(member.pk for member in members)
        self.service_state = service_model.objects.values().get(pk=self.service.pk)

    def tearDown(self):
        try:
            MigrationExecutor(connection).migrate(self.latest_targets)
        finally:
            super().tearDown()

    def test_about_copy_timestamps_and_service_team_links_survive_schema_change(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        migrated_apps = executor.loader.project_state(self.migrate_to).apps
        about_model = migrated_apps.get_model("website", "About")
        service_model = migrated_apps.get_model("website", "Service")
        self.assertEqual(about_model.objects.count(), len(self.existing_about))
        for original in self.existing_about:
            with self.subTest(about_id=original["id"]):
                migrated = about_model.objects.values().get(pk=original["id"])
                for name, value in original.items():
                    self.assertEqual(migrated[name], value)
                for name, value in CurrentAbout.HERO_DEFAULTS.items():
                    self.assertEqual(migrated[name], value)

        service = service_model.objects.get(pk=self.service.pk)
        self.assertEqual(
            service_model.objects.values().get(pk=service.pk), self.service_state
        )
        self.assertEqual(
            list(service.doctors.order_by("pk").values_list("pk", flat=True)),
            self.member_ids,
        )
        self.assertTrue(service_model._meta.get_field("doctors").blank)
