from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_administrator_role_status_audit"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="AdministratorStatusAudit",
            new_name="AdministratorAccessAudit",
        ),
        migrations.AddField(
            model_name="administratoraccessaudit",
            name="new_role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("front_desk", "Front Desk"),
                    ("content_manager", "Content Manager"),
                    ("auditor", "Read-only Auditor"),
                    ("super_admin", "Super Admin"),
                ],
                max_length=30,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="administratoraccessaudit",
            name="previous_role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("front_desk", "Front Desk"),
                    ("content_manager", "Content Manager"),
                    ("auditor", "Read-only Auditor"),
                    ("super_admin", "Super Admin"),
                ],
                max_length=30,
                null=True,
            ),
        ),
    ]
