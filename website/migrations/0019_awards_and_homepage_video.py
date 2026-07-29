from django.db import migrations, models


def seed_awards_and_video(apps, schema_editor):
    Award = apps.get_model("website", "Award")
    HomepageVideo = apps.get_model("website", "HomepageVideo")

    HomepageVideo.objects.get_or_create(
        youtube_url="https://youtu.be/ZBcjm8dh1T4",
        defaults={
            "eyebrow": "Inside Sinel",
            "title": "The New Sinel",
            "description": (
                "Take a closer look at our expanded hospital, the people "
                "behind your care and the facilities supporting families "
                "around the clock."
            ),
            "poster_url": (
                "https://sinel-hospital.web.app/resources/vid.jpg"
            ),
            "poster": "uploads/videos/the-new-sinel.jpg",
            "visible": True,
        },
    )

    award_sources = [
        (
            "uploads/awards/sinel-award-01.jpg",
            "https://sinel-hospital.web.app/images/awards/IMG_8086.jpg.jpeg",
        ),
        (
            "uploads/awards/sinel-award-02.jpg",
            "https://sinel-hospital.web.app/images/awards/IMG_8092.jpg.jpeg",
        ),
        (
            "uploads/awards/sinel-award-03.jpg",
            "https://sinel-hospital.web.app/images/awards/IMG_8094.jpg.jpeg",
        ),
        (
            "uploads/awards/sinel-award-04.jpg",
            "https://sinel-hospital.web.app/images/awards/IMG_8095.jpg.jpeg",
        ),
        (
            "uploads/awards/sinel-award-05.jpg",
            "https://sinel-hospital.web.app/images/awards/IMG_8096.jpg.jpeg",
        ),
        (
            "uploads/awards/sinel-award-06.jpg",
            "https://sinel-hospital.web.app/images/awards/IMG_8097.jpg.jpeg",
        ),
        (
            "uploads/awards/sinel-award-07.jpg",
            "https://sinel-hospital.web.app/images/awards/IMG_8099.jpg.jpeg",
        ),
    ]
    for index, (image, image_url) in enumerate(award_sources, start=1):
        Award.objects.get_or_create(
            image_url=image_url,
            defaults={
                "title": f"Sinel Hospital recognition {index}",
                "image": image,
                "position": index * 10,
                "visible": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0018_homepage_content"),
    ]

    operations = [
        migrations.CreateModel(
            name="Award",
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
                ("title", models.CharField(max_length=150)),
                (
                    "issuer",
                    models.CharField(
                        blank=True,
                        help_text=(
                            "Optional organisation or programme that issued it."
                        ),
                        max_length=150,
                    ),
                ),
                (
                    "year",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        null=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional context visitors should know.",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="uploads/awards",
                    ),
                ),
                (
                    "image_url",
                    models.URLField(
                        blank=True,
                        help_text=(
                            "Optional fallback when no image has been uploaded."
                        ),
                        max_length=500,
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
            ],
            options={
                "ordering": ("position", "-year", "id"),
            },
        ),
        migrations.CreateModel(
            name="HomepageVideo",
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
                    "eyebrow",
                    models.CharField(
                        default="Inside Sinel",
                        max_length=60,
                    ),
                ),
                ("title", models.CharField(max_length=150)),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text=(
                            "A short introduction shown beside the video."
                        ),
                    ),
                ),
                (
                    "youtube_url",
                    models.URLField(
                        help_text=(
                            "Use a YouTube watch, share, Shorts, or embed URL."
                        ),
                        max_length=300,
                    ),
                ),
                (
                    "poster",
                    models.ImageField(
                        blank=True,
                        help_text=(
                            "Recommended: a 16:9 landscape image."
                        ),
                        null=True,
                        upload_to="uploads/videos",
                    ),
                ),
                (
                    "poster_url",
                    models.URLField(
                        blank=True,
                        help_text=(
                            "Optional fallback when no poster has been uploaded."
                        ),
                        max_length=500,
                    ),
                ),
                ("visible", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("-updated_at", "-id"),
            },
        ),
        migrations.RunPython(
            seed_awards_and_video,
            migrations.RunPython.noop,
        ),
    ]
