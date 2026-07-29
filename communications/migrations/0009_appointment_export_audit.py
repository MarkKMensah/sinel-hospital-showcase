from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("communications", "0008_appointment_workflow"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppointmentExportAudit",
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
                ("filters", models.JSONField(blank=True, default=dict)),
                (
                    "record_count",
                    models.PositiveIntegerField(default=0),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "exported_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="appointment_exports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
            },
        ),
    ]
