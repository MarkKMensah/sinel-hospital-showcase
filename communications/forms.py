from datetime import datetime

from django import forms
from django.utils import timezone

from .models import Appointment
from website.models import Service


class AppointmentForm(forms.ModelForm):
    appointment_datetime = forms.DateTimeField(
        label="Preferred appointment date and time",
        input_formats=(
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
        ),
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                "class": "form-control",
                "type": "datetime-local",
                "autocomplete": "off",
            },
        ),
    )

    class Meta:
        model = Appointment
        fields = [
            "fullname",
            "email",
            "number",
            "date_of_birth",
            "message",
            "service",
        ]

    def __init__(self, *args, **kwargs):
        data = args[0] if args else kwargs.get("data")
        if data is not None and not data.get("appointment_datetime"):
            legacy_date = data.get("date")
            legacy_time = data.get("time")
            if legacy_date and legacy_time:
                data = data.copy()
                data["appointment_datetime"] = (
                    f"{legacy_date}T{legacy_time}"
                )
                if args:
                    args = (data, *args[1:])
                else:
                    kwargs["data"] = data

        super().__init__(*args, **kwargs)
        self.fields["appointment_datetime"].widget.attrs["min"] = (
            timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        )

        if self.instance.pk and not self.is_bound:
            self.initial["appointment_datetime"] = datetime.combine(
                self.instance.date,
                self.instance.time,
            )

    def clean_appointment_datetime(self):
        preferred_datetime = self.cleaned_data["appointment_datetime"]
        if preferred_datetime < timezone.now():
            raise forms.ValidationError(
                "Choose a future appointment date and time."
            )
        return preferred_datetime

    def clean_service(self):
        service = self.cleaned_data["service"].strip()
        if service.lower() == "other":
            return "Other"
        if not Service.objects.filter(
            title=service,
            visible=True,
        ).exists():
            raise forms.ValidationError("Choose an available service.")
        return service

    def save(self, commit=True):
        appointment = super().save(commit=False)
        preferred_datetime = timezone.localtime(
            self.cleaned_data["appointment_datetime"]
        )
        appointment.date = preferred_datetime.date()
        appointment.time = preferred_datetime.time().replace(tzinfo=None)
        if commit:
            appointment.save()
            self.save_m2m()
        return appointment
