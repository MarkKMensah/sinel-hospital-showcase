from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login", views.LoginView.as_view(), name="login"),
    path("change_password",
         views.ChangePasswordView.as_view(),
         name="change_password"),
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("administrators",
         views.AdministratorsView.as_view(),
         name="administrators"),
    path(
        "administrator_details/<int:admin_id>",
        views.AdministratorDetailsView.as_view(),
        name="administrator_details",
    ),
    path(
        "create_administrator",
        views.CreateAdministrator.as_view(),
        name="create_administrator",
    ),
]
