from django.db import models
from django.utils import timezone


# Create your models here.
class Appointment(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    fullname = models.CharField(max_length=70)
    email = models.EmailField(max_length=254, blank=True, null=True)
    number = models.CharField(max_length=13)  #Incase of +233
    date = models.DateField(default=timezone.now)
    time = models.TimeField(default=timezone.now)
    date_of_birth = models.DateField(null=True, blank=True)
    message = models.TextField()
    service = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        "accounts.Administrator",
        related_name="assigned_appointments",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    internal_notes = models.TextField(blank=True, default="")
    status_updated_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.fullname


class AppointmentStatusAudit(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        related_name="status_audits",
        on_delete=models.CASCADE,
    )
    changed_by = models.ForeignKey(
        "accounts.Administrator",
        related_name="appointment_status_changes",
        null=True,
        on_delete=models.SET_NULL,
    )
    previous_status = models.CharField(
        max_length=20,
        choices=Appointment.Status.choices,
    )
    new_status = models.CharField(
        max_length=20,
        choices=Appointment.Status.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return (
            f"Appointment {self.appointment_id}: "
            f"{self.previous_status} -> {self.new_status}"
        )


class AppointmentExportAudit(models.Model):
    exported_by = models.ForeignKey(
        "accounts.Administrator",
        related_name="appointment_exports",
        null=True,
        on_delete=models.SET_NULL,
    )
    filters = models.JSONField(default=dict, blank=True)
    record_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return f"{self.exported_by}: {self.record_count} appointment(s)"
