from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_administrator_role_status_audit"),
        ("communications", "0007_auto_20220220_1639"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_appointments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="internal_notes",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="appointment",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("contacted", "Contacted"),
                    ("confirmed", "Confirmed"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                    ("no_show", "No-show"),
                ],
                db_index=True,
                default="new",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="status_updated_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.CreateModel(
            name="AppointmentStatusAudit",
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
                    "previous_status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("contacted", "Contacted"),
                            ("confirmed", "Confirmed"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                            ("no_show", "No-show"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "new_status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("contacted", "Contacted"),
                            ("confirmed", "Confirmed"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                            ("no_show", "No-show"),
                        ],
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "appointment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_audits",
                        to="communications.appointment",
                    ),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="appointment_status_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
            },
        ),
    ]
