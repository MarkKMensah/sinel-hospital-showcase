from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0019_awards_and_homepage_video"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepageshortcut",
            name="ribbon_position",
            field=models.CharField(
                choices=[
                    ("right", "Top right"),
                    ("left", "Top left"),
                ],
                default="right",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="homepageshortcut",
            name="ribbon_style",
            field=models.CharField(
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
        migrations.AddField(
            model_name="homepageshortcut",
            name="ribbon_text",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Optional. Try New, Featured, Popular, 24/7, "
                    "or add your own."
                ),
                max_length=24,
            ),
        ),
    ]
