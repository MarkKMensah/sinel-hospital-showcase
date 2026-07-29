from datetime import datetime, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from communications.models import Appointment
from website.models import Service


class PublicAppointmentBookingTests(TestCase):
    def setUp(self):
        self.service = Service.objects.create(
            title="General Consultation",
            description="<p>General care.</p>",
            schedules="<p>Daily</p>",
            image="uploads/images/general.jpg",
            visible=True,
        )

    def valid_payload(self):
        preferred_datetime = timezone.now() + timedelta(days=1)
        return {
            "fullname": "Patient Example",
            "email": "patient@example.test",
            "number": "+233200000002",
            "appointment_datetime": preferred_datetime.strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "date_of_birth": "1990-01-01",
            "message": "I would like a consultation.",
            "service": self.service.title,
        }

    def test_valid_booking_is_created_with_new_status_and_notice(self):
        payload = self.valid_payload()
        payload["status"] = Appointment.Status.COMPLETED

        response = self.client.post(
            reverse("communications:book_appointment"),
            payload,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.status, Appointment.Status.NEW)
        expected_datetime = datetime.strptime(
            payload["appointment_datetime"],
            "%Y-%m-%dT%H:%M",
        )
        self.assertEqual(
            datetime.combine(appointment.date, appointment.time).replace(
                second=0,
                microsecond=0,
            ),
            expected_datetime,
        )
        self.assertContains(
            response,
            "appointment request was submitted successfully",
        )

    def test_past_appointment_datetime_is_rejected_without_losing_form(self):
        payload = self.valid_payload()
        payload["appointment_datetime"] = (
            timezone.now() - timedelta(days=1)
        ).strftime("%Y-%m-%dT%H:%M")

        response = self.client.post(
            reverse("communications:book_appointment"),
            payload,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Appointment.objects.exists())
        self.assertContains(
            response,
            "Choose a future appointment date and time.",
            status_code=400,
        )

    def test_hidden_or_unknown_service_is_rejected(self):
        payload = self.valid_payload()
        payload["service"] = "Unpublished Service"

        response = self.client.post(
            reverse("communications:book_appointment"),
            payload,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Appointment.objects.exists())
        self.assertContains(
            response,
            "Choose an available service.",
            status_code=400,
        )

    def test_legacy_separate_date_and_time_submission_still_works(self):
        payload = self.valid_payload()
        payload.pop("appointment_datetime")
        payload["date"] = timezone.localdate() + timedelta(days=2)
        payload["time"] = "09:30"

        response = self.client.post(
            reverse("communications:book_appointment"),
            payload,
        )

        self.assertEqual(response.status_code, 302)
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.date, payload["date"])
        self.assertEqual(appointment.time, time(9, 30))

    def test_booking_page_has_one_combined_appointment_control(self):
        response = self.client.get(
            reverse("communications:book_appointment")
        )

        self.assertContains(response, 'name="appointment_datetime"')
        self.assertContains(response, 'type="datetime-local"')
        self.assertNotContains(response, 'name="time"')
