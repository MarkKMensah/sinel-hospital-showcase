from django.urls import path
from . import views

app_name = "communications"
urlpatterns = [
    path("book_appointment", views.BookAppointment.as_view(), name="book_appointment")
]
