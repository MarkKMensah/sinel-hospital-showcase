import django.db.models.deletion
from django.db import migrations, models


def seed_homepage_shortcuts(apps, schema_editor):
    Service = apps.get_model("website", "Service")
    HomepageShortcut = apps.get_model("website", "HomepageShortcut")
    if HomepageShortcut.objects.exists():
        return

    seeds = [
        (
            "primary healthcare",
            "heart-pulse",
            "sky",
            "Round-the-clock general consultation for everyday health needs.",
        ),
        (
            "gynecology",
            "gender-female",
            "navy",
            "Specialist women's healthcare delivered with privacy and respect.",
        ),
        (
            "pharmacy",
            "capsule-pill",
            "teal",
            "Reliable pharmacy support, day and night.",
        ),
        (
            "emergency",
            "activity",
            "red",
            "Rapid emergency and intensive care when every minute matters.",
        ),
        (
            "antenatal",
            "person-hearts",
            "gold",
            "Attentive care for mothers and babies throughout pregnancy.",
        ),
    ]

    for position, (keyword, icon, accent, description) in enumerate(
        seeds,
        start=1,
    ):
        service = (
            Service.objects.filter(
                visible=True,
                title__icontains=keyword,
            )
            .order_by("id")
            .first()
        )
        if service:
            HomepageShortcut.objects.create(
                service=service,
                description=description,
                icon=icon,
                accent=accent,
                position=position * 10,
                visible=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0017_alter_contact_telephone"),
    ]

    operations = [
        migrations.AlterField(
            model_name="banner",
            name="description",
            field=models.CharField(
                blank=True,
                max_length=200,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="banner",
            name="url",
            field=models.URLField(
                blank=True,
                help_text=(
                    "Optional. A selected service takes priority over this URL."
                ),
                max_length=200,
                null=True,
                verbose_name="External button URL",
            ),
        ),
        migrations.AddField(
            model_name="banner",
            name="button_label",
            field=models.CharField(
                default="Explore our services",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="banner",
            name="position",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Lower numbers appear first.",
            ),
        ),
        migrations.AddField(
            model_name="banner",
            name="service",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="homepage_banners",
                to="website.service",
            ),
        ),
        migrations.AlterModelOptions(
            name="banner",
            options={"ordering": ("position", "-updated_at", "-id")},
        ),
        migrations.CreateModel(
            name="HomepageShortcut",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "label",
                    models.CharField(
                        blank=True,
                        help_text="Leave blank to use the service title.",
                        max_length=100,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        blank=True,
                        help_text=(
                            "Leave blank to use a short excerpt from the service."
                        ),
                        max_length=200,
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        choices=[
                            ("heart-pulse", "Heart pulse"),
                            ("hospital", "Hospital"),
                            ("capsule-pill", "Pharmacy"),
                            ("gender-female", "Women's health"),
                            ("person-hearts", "Family care"),
                            ("activity", "Emergency"),
                            ("clipboard2-pulse", "Laboratory"),
                            ("sun", "Wellness"),
                            ("telephone", "Telephone"),
                            ("shield-plus", "Protection"),
                        ],
                        default="heart-pulse",
                        max_length=30,
                    ),
                ),
                (
                    "accent",
                    models.CharField(
                        choices=[
                            ("sky", "Sinel blue"),
                            ("navy", "Navy"),
                            ("red", "Emergency red"),
                            ("teal", "Teal"),
                            ("gold", "Gold"),
                        ],
                        default="sky",
                        max_length=20,
                    ),
                ),
                (
                    "position",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Lower numbers appear first.",
                    ),
                ),
                ("visible", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="homepage_shortcuts",
                        to="website.service",
                    ),
                ),
            ],
            options={"ordering": ("position", "id")},
        ),
        migrations.RunPython(
            seed_homepage_shortcuts,
            migrations.RunPython.noop,
        ),
    ]
