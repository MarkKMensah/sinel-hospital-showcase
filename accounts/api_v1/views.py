from rest_framework import generics, permissions, status
from rest_framework.response import Response
from accounts.api_v1.serializers import (AdministratorSerializer,
                                         ChangeAdministratorPasswordSerializer,
                                         LoginSerializer, RegisterSerializer)
from accounts.api_v1.permissions import IsActiveStaff, IsActiveSuperuser
from accounts.forms import AdministratorForm
from accounts.models import Administrator
from knox.models import AuthToken


class RegisterAdministrator(generics.GenericAPIView):
    """Create an administrator account as an active superuser."""

    permission_classes = [IsActiveSuperuser]
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        response_data = {
            "error_message": None,
            "administrator": AdministratorSerializer(
                user,
                context={
                    "request": request
                },
            ).data,
            "token": None,
        }
        return Response(
            {"response": response_data},
            status=status.HTTP_201_CREATED,
        )


class LoginAdministratorApi(generics.GenericAPIView):
    """An API end point to allow registered administrators to login"""

    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data
        AuthToken.objects.filter(user=user).delete()
        response_data = {
            "error_message":
            None,
            "administrator":
            AdministratorSerializer(
                user,
                context={
                    "request": request
                },
            ).data,
            "token":
            AuthToken.objects.create(user)[1],
        }
        return Response({"response": response_data}, status=status.HTTP_200_OK)


class AdministratorsApi(generics.GenericAPIView):
    """
    Returns the list of all administrators
    """
    permission_classes = [IsActiveSuperuser]
    serializer_class = AdministratorSerializer
    form_class = AdministratorForm

    def get(self, request, **kwargs):
        administrators = Administrator.objects.all()
        data = self.serializer_class(administrators,
                                     context={
                                         "request": request
                                     },
                                     many=True).data
        return Response({"administrators": data})


class RetrieveAdministrator(generics.GenericAPIView):
    """
    Returns the details of an administrator.
    """
    permission_classes = [IsActiveSuperuser]
    serializer_class = AdministratorSerializer

    def get(self, request, email_address, **kwargs):
        administrator = generics.get_object_or_404(Administrator,
                                                   email_address=email_address)
        data = self.serializer_class(administrator,
                                     context={
                                         "request": request
                                     }).data
        return Response({"administrator": data})


class MyAccount(generics.GenericAPIView):
    """
    Returns the details of an administrator.
    """
    permission_classes = [IsActiveStaff]
    serializer_class = AdministratorSerializer

    def get(self, request, **kwargs):
        data = self.serializer_class(request.user,
                                     context={
                                         "request": request
                                     }).data
        return Response({"administrator": data})


class ChangeAdministratorPasswordApi(generics.GenericAPIView):
    """
    Change the password of an administrator.
    """
    permission_classes = [IsActiveStaff]
    serializer_class = ChangeAdministratorPasswordSerializer

    def post(self, request, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data.get("old_password", "")
        new_password = serializer.validated_data["new_password"]
        email_address = serializer.validated_data["email_address"]

        administrator = generics.get_object_or_404(Administrator,
                                                   email_address=email_address)

        changing_own_password = request.user.pk == administrator.pk
        if not changing_own_password and not request.user.is_superuser:
            return Response(
                {"detail": "You cannot change another user's password."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if changing_own_password and not administrator.check_password(old_password):
            return Response(
                {"detail": "Incorrect credentials."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        administrator.set_password(new_password)
        administrator.save(update_fields=["password", "updated_at"])

        # Invalidate every existing API session for the changed account.
        AuthToken.objects.filter(user=administrator).delete()
        token = None
        if changing_own_password:
            token = AuthToken.objects.create(administrator)[1]

        response_data = {
            "error_message": None,
            "administrator": AdministratorSerializer(
                administrator,
                context={
                    "request": request
                },
            ).data,
            "token": token,
        }
        return Response({"response": response_data}, status=status.HTTP_200_OK)
