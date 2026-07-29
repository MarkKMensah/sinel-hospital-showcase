from django.urls import path
from . import views

app_name = "website"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("about", views.AboutView.as_view(), name="about"),
    path("contact", views.ContactView.as_view(), name="contact"),
    path("gallery", views.GalleryView.as_view(), name="gallery"),
    path("services", views.ServicesView.as_view(), name="services"),
    path("teams", views.DoctorsView.as_view(), name="doctors"),
    path("our-partners", views.OurPatnersView.as_view(), name="partners"),
    path("services/<str:service_id>/details",
         views.ServiceDetailsView.as_view(),
         name="service_details"),
    path("more-pages/<str:page_id>/<str:slug>",
         views.StaticPageView.as_view(),
         name="static_page_view")
]
