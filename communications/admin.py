from django.contrib import admin

from communications.models import (
    Appointment,
    AppointmentExportAudit,
    AppointmentStatusAudit,
)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "fullname",
        "service",
        "date",
        "time",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "service", "date")
    search_fields = ("fullname", "email", "number", "service")


@admin.register(AppointmentStatusAudit)
class AppointmentStatusAuditAdmin(admin.ModelAdmin):
    list_display = (
        "appointment",
        "previous_status",
        "new_status",
        "changed_by",
        "created_at",
    )
    list_filter = ("previous_status", "new_status")
    readonly_fields = (
        "appointment",
        "previous_status",
        "new_status",
        "changed_by",
        "created_at",
    )


@admin.register(AppointmentExportAudit)
class AppointmentExportAuditAdmin(admin.ModelAdmin):
    list_display = (
        "exported_by",
        "record_count",
        "created_at",
    )
    readonly_fields = (
        "exported_by",
        "filters",
        "record_count",
        "created_at",
    )
