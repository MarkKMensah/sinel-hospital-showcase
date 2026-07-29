from django.contrib import messages
from django.shortcuts import redirect, render

from website.models import Service
from .forms import AppointmentForm
from django.views.generic import View


# Create your views here.
class BookAppointment(View):
    template_name = "communications/appointments.html"
    form_class = AppointmentForm

    def get(self, request, *args, **kwargs):
        services = Service.objects.filter(visible=True)
        context = {
            "services": services,
            "form": self.form_class(),
        }
        return render(request, self.template_name, context)

    def post(self, request, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                (
                    "Your appointment request was submitted successfully. "
                    "A Sinel representative will contact you to confirm it."
                ),
            )
            return redirect("communications:book_appointment")
        return render(
            request,
            self.template_name,
            {
                "services": Service.objects.filter(visible=True),
                "form": form,
            },
            status=400,
        )
