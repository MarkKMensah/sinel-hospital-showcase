from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def assign_existing_roles(apps, schema_editor):
    Administrator = apps.get_model("accounts", "Administrator")
    Administrator.objects.filter(is_superuser=True).update(role="super_admin")
    Administrator.objects.filter(
        is_superuser=False,
        title__iregex=r"(front[\s-]?desk|reception|client service)",
    ).update(role="front_desk")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_administrator_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="administrator",
            name="role",
            field=models.CharField(
                choices=[
                    ("front_desk", "Front Desk"),
                    ("content_manager", "Content Manager"),
                    ("auditor", "Read-only Auditor"),
                    ("super_admin", "Super Admin"),
                ],
                default="content_manager",
                max_length=30,
            ),
        ),
        migrations.RunPython(
            assign_existing_roles,
            migrations.RunPython.noop,
        ),
        migrations.CreateModel(
            name="AdministratorStatusAudit",
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
                ("previous_is_active", models.BooleanField()),
                ("new_is_active", models.BooleanField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "administrator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_audits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "changed_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="administrator_status_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
            },
        ),
    ]
