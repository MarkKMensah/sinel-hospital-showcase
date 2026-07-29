from django.db import models
from django.contrib.auth.models import PermissionsMixin, AbstractBaseUser
from .managers import AdministratorManager


class Administrator(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        FRONT_DESK = "front_desk", "Front Desk"
        CONTENT_MANAGER = "content_manager", "Content Manager"
        AUDITOR = "auditor", "Read-only Auditor"
        SUPER_ADMIN = "super_admin", "Super Admin"

    fullname = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    email_address = models.EmailField(unique=True)
    photo = models.ImageField(upload_to="uploads/users", blank=True, null=True)
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.CONTENT_MANAGER,
    )
    last_login_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    username = None
    USERNAME_FIELD = "email_address"
    objects = AdministratorManager()
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.fullname or self.email_address

    @property
    def can_view_appointments(self):
        return self.is_superuser or self.role in {
            self.Role.FRONT_DESK,
            self.Role.AUDITOR,
        }

    @property
    def can_manage_appointments(self):
        return self.is_superuser or self.role == self.Role.FRONT_DESK

    @property
    def can_view_content(self):
        return self.is_superuser or self.role in {
            self.Role.CONTENT_MANAGER,
            self.Role.AUDITOR,
        }

    @property
    def can_manage_content(self):
        return self.is_superuser or self.role == self.Role.CONTENT_MANAGER


class AdministratorAccessAudit(models.Model):
    administrator = models.ForeignKey(
        Administrator,
        related_name="status_audits",
        on_delete=models.CASCADE,
    )
    changed_by = models.ForeignKey(
        Administrator,
        related_name="administrator_status_changes",
        null=True,
        on_delete=models.SET_NULL,
    )
    previous_is_active = models.BooleanField()
    new_is_active = models.BooleanField()
    previous_role = models.CharField(
        max_length=30,
        choices=Administrator.Role.choices,
        null=True,
        blank=True,
    )
    new_role = models.CharField(
        max_length=30,
        choices=Administrator.Role.choices,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self):
        return (
            f"{self.administrator}: "
            f"{self.previous_role}/{self.previous_is_active} -> "
            f"{self.new_role}/{self.new_is_active}"
        )
