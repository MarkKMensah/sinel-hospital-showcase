from django.db import migrations


def restore_legacy_administrator_staff_access(apps, schema_editor):
    Administrator = apps.get_model("accounts", "Administrator")
    Administrator.objects.filter(is_staff=False).update(is_staff=True)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_administrator_access_audit"),
    ]

    operations = [
        migrations.RunPython(
            restore_legacy_administrator_staff_access,
            migrations.RunPython.noop,
        ),
    ]
