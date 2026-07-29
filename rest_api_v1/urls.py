from django.urls import path
from website.api_v1 import views as website_api
from accounts.api_v1 import views as account_api

urlpatterns = [
    path("contact", website_api.ContactApi.as_view()),
    path("about", website_api.AboutAPI.as_view()),
    path("administrators", account_api.AdministratorsApi.as_view()),
    path("my_account", account_api.MyAccount.as_view()),
    path("administrators/<str:email_address>", account_api.RetrieveAdministrator.as_view()),
    path("administrators/register/", account_api.RegisterAdministrator.as_view()),
    path("administrators/login/", account_api.LoginAdministratorApi.as_view()),
    path("administrators/change_password/", account_api.ChangeAdministratorPasswordApi.as_view()),

    path("gallery", website_api.MediaAPI.as_view()),
    path("services", website_api.ServicesAPI.as_view()),
    path("team_leads", website_api.TeamLeadsAPI.as_view()),
    path("clients", website_api.ClientsAPI.as_view()),
    path("opening_hours", website_api.OpeningHoursAPI.as_view()),
    path("social_media_links", website_api.SocialMediaLinksAPI.as_view()),
]