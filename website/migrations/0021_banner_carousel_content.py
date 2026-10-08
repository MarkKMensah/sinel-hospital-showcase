from django.core.validators import URLValidator
from django.db import migrations, models


def preserve_existing_banner_copy(apps, schema_editor):
    Banner = apps.get_model("website", "Banner")
    banners = Banner.objects.using(schema_editor.connection.alias)
    banners.update(eyebrow="Specialist family care in Tema")
    banners.filter(description__isnull=True).update(
        description="Trusted, compassionate care for every stage of life—from us to you."
    )
    banners.filter(description="").update(
        description="Trusted, compassionate care for every stage of life—from us to you."
    )


class Migration(migrations.Migration):
    dependencies = [("website", "0020_homepageshortcut_ribbon")]

    operations = [
        migrations.AddField(
            model_name="banner",
            name="eyebrow",
            field=models.CharField(
                blank=True,
                default="",
                db_default="",
                help_text="Optional small heading above the headline.",
                max_length=80,
            ),
        ),
        migrations.AlterField(
            model_name="banner",
            name="url",
            field=models.URLField(
                "External button URL",
                blank=True,
                null=True,
                max_length=200,
                help_text="Optional. A selected service takes priority over this URL.",
                validators=[URLValidator(schemes=["http", "https"])],
            ),
        ),
        migrations.AlterModelOptions(
            name="banner",
            options={"ordering": ("position", "id")},
        ),
        migrations.RunPython(
            preserve_existing_banner_copy,
            migrations.RunPython.noop,
        ),
    ]
