from django.contrib import admin

from .models import Administrator, AdministratorAccessAudit


@admin.register(Administrator)
class AdministratorAdmin(admin.ModelAdmin):
    list_display = (
        "email_address",
        "fullname",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email_address", "fullname", "title")


@admin.register(AdministratorAccessAudit)
class AdministratorAccessAuditAdmin(admin.ModelAdmin):
    list_display = (
        "administrator",
        "previous_is_active",
        "new_is_active",
        "previous_role",
        "new_role",
        "changed_by",
        "created_at",
    )
    list_filter = (
        "previous_is_active",
        "new_is_active",
        "previous_role",
        "new_role",
    )
    readonly_fields = (
        "administrator",
        "previous_is_active",
        "new_is_active",
        "previous_role",
        "new_role",
        "changed_by",
        "created_at",
    )
