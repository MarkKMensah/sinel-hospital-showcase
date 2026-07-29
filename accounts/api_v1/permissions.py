from rest_framework.permissions import BasePermission


class IsActiveStaff(BasePermission):
    message = "Active staff access is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
        )


class IsActiveSuperuser(BasePermission):
    message = "Active superuser access is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_superuser
        )


class IsContentManager(BasePermission):
    message = "Content manager access is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
            and user.can_manage_content
        )
