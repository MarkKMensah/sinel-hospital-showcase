from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from knox.models import AuthToken
from rest_framework.test import APIClient

from accounts.models import Administrator, AdministratorAccessAudit


PASSWORD = "Containment!Pass2026"
NEW_PASSWORD = "Z9!Containment-Unique-2026"


def create_administrator(email, **overrides):
    defaults = {
        "password": PASSWORD,
        "fullname": email.split("@")[0].title(),
        "title": "Administrator",
        "is_active": True,
        "is_staff": True,
        "is_superuser": False,
    }
    if overrides.get("is_superuser") and "role" not in overrides:
        defaults["role"] = Administrator.Role.SUPER_ADMIN
    defaults.update(overrides)
    return Administrator.objects.create_user(
        email_address=email,
        **defaults,
    )


class WebAdministratorContainmentTests(TestCase):
    def setUp(self):
        self.superuser = create_administrator(
            "owner@example.test",
            is_superuser=True,
        )
        self.staff = create_administrator("staff@example.test")
        self.regular_user = create_administrator(
            "regular@example.test",
            is_staff=False,
        )

    def test_dashboard_login_rejects_non_staff_user(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "email_address": self.regular_user.email_address,
                "password": PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_page_uses_restrained_staff_layout(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back")
        self.assertContains(response, "Sign in to dashboard")
        self.assertNotContains(response, "Secure staff access")
        self.assertNotContains(response, "sinel-login-lock")
        self.assertNotContains(response, "bi-arrow-right")
        self.assertContains(response, "login_refresh.css")
        self.assertContains(response, 'autocomplete="current-password"')
        self.assertNotContains(response, "Role-based access")
        self.assertNotContains(response, "Appointment workflow")
        self.assertNotContains(response, "Website content management")

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            f"{reverse('accounts:login')}?next=https://example.org/escape",
            {
                "email_address": self.superuser.email_address,
                "password": PASSWORD,
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard:index"),
            fetch_redirect_response=False,
        )

    def test_unchecked_status_deactivates_user_and_invalidates_tokens(self):
        AuthToken.objects.create(self.staff)
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "accounts:administrator_details",
                args=[self.staff.pk],
            ),
            {
                "fullname": self.staff.fullname,
                "title": self.staff.title,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_active)
        self.assertFalse(AuthToken.objects.filter(user=self.staff).exists())
        self.assertContains(response, "was deactivated successfully")
        audit = AdministratorAccessAudit.objects.get(
            administrator=self.staff
        )
        self.assertEqual(audit.changed_by, self.superuser)
        self.assertTrue(audit.previous_is_active)
        self.assertFalse(audit.new_is_active)
        self.assertEqual(
            audit.previous_role,
            Administrator.Role.CONTENT_MANAGER,
        )
        self.assertEqual(
            audit.new_role,
            Administrator.Role.CONTENT_MANAGER,
        )

    def test_superuser_cannot_deactivate_own_account(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "accounts:administrator_details",
                args=[self.superuser.pk],
            ),
            {
                "fullname": self.superuser.fullname,
                "title": self.superuser.title,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)

    def test_role_change_is_audited(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "accounts:administrator_details",
                args=[self.staff.pk],
            ),
            {
                "fullname": self.staff.fullname,
                "title": self.staff.title,
                "role": Administrator.Role.FRONT_DESK,
                "is_active": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.role, Administrator.Role.FRONT_DESK)
        audit = AdministratorAccessAudit.objects.get(
            administrator=self.staff
        )
        self.assertEqual(
            audit.previous_role,
            Administrator.Role.CONTENT_MANAGER,
        )
        self.assertEqual(
            audit.new_role,
            Administrator.Role.FRONT_DESK,
        )
        self.assertContains(
            response,
            "dashboard role was updated to Front Desk",
        )

    def test_assigning_role_restores_legacy_staff_access(self):
        legacy_admin = create_administrator(
            "legacy@example.test",
            is_staff=False,
        )
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse(
                "accounts:administrator_details",
                args=[legacy_admin.pk],
            ),
            {
                "fullname": legacy_admin.fullname,
                "title": legacy_admin.title,
                "role": Administrator.Role.CONTENT_MANAGER,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        legacy_admin.refresh_from_db()
        self.assertTrue(legacy_admin.is_staff)
        self.assertTrue(legacy_admin.is_active)
        self.assertEqual(
            legacy_admin.role,
            Administrator.Role.CONTENT_MANAGER,
        )

    def test_web_created_administrator_is_staff(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("accounts:create_administrator"),
            {
                "email_address": "created@example.test",
                "fullname": "Created Administrator",
                "title": "Content Editor",
                "password": NEW_PASSWORD,
                "repeat_password": NEW_PASSWORD,
                "is_active": "on",
                "role": Administrator.Role.FRONT_DESK,
            },
        )

        self.assertRedirects(response, reverse("accounts:administrators"))
        created = Administrator.objects.get(
            email_address="created@example.test"
        )
        self.assertTrue(created.is_staff)
        self.assertFalse(created.is_superuser)
        self.assertEqual(created.role, Administrator.Role.FRONT_DESK)

    def test_logout_requires_post(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("accounts:logout"))

        self.assertEqual(response.status_code, 405)


class AdministratorApiContainmentTests(TestCase):
    def setUp(self):
        self.superuser = create_administrator(
            "api-owner@example.test",
            is_superuser=True,
        )
        self.staff = create_administrator("api-staff@example.test")
        self.other_staff = create_administrator("api-other@example.test")
        self.regular_user = create_administrator(
            "api-regular@example.test",
            is_staff=False,
        )
        self.client = APIClient()

    def test_anonymous_registration_is_closed(self):
        response = self.client.post(
            "/api/v1/administrators/register/",
            {
                "email_address": "intruder@example.test",
                "fullname": "Intruder",
                "password": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(
            Administrator.objects.filter(
                email_address="intruder@example.test"
            ).exists()
        )

    def test_non_superuser_cannot_register_administrator(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            "/api/v1/administrators/register/",
            {
                "email_address": "blocked@example.test",
                "fullname": "Blocked",
                "password": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_superuser_registration_creates_staff_without_target_token(self):
        self.client.force_authenticate(user=self.superuser)

        response = self.client.post(
            "/api/v1/administrators/register/",
            {
                "email_address": "new-api-staff@example.test",
                "fullname": "New API Staff",
                "title": "Content Editor",
                "password": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        created = Administrator.objects.get(
            email_address="new-api-staff@example.test"
        )
        self.assertTrue(created.is_staff)
        self.assertIsNone(response.data["response"]["token"])
        self.assertFalse(AuthToken.objects.filter(user=created).exists())

    def test_regular_user_cannot_access_staff_api(self):
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get("/api/v1/my_account")

        self.assertEqual(response.status_code, 403)

    def test_api_login_rejects_non_staff_user(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/v1/administrators/login/",
            {
                "email_address": self.regular_user.email_address,
                "password": PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            AuthToken.objects.filter(user=self.regular_user).exists()
        )

    def test_api_login_rotates_existing_staff_token(self):
        AuthToken.objects.create(self.staff)
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/v1/administrators/login/",
            {
                "email_address": self.staff.email_address,
                "password": PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AuthToken.objects.filter(user=self.staff).count(), 1)
        self.assertIsNotNone(response.data["response"]["token"])

    def test_staff_cannot_list_all_administrators(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get("/api/v1/administrators")

        self.assertEqual(response.status_code, 403)

    def test_staff_cannot_change_another_users_password(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            "/api/v1/administrators/change_password/",
            {
                "email_address": self.other_staff.email_address,
                "old_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.other_staff.refresh_from_db()
        self.assertTrue(self.other_staff.check_password(PASSWORD))

    def test_self_password_change_requires_old_password(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            "/api/v1/administrators/change_password/",
            {
                "email_address": self.staff.email_address,
                "old_password": "incorrect",
                "new_password": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password(PASSWORD))

    def test_self_password_change_replaces_only_own_token(self):
        AuthToken.objects.create(self.staff)
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            "/api/v1/administrators/change_password/",
            {
                "email_address": self.staff.email_address,
                "old_password": PASSWORD,
                "new_password": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password(NEW_PASSWORD))
        self.assertIsNotNone(response.data["response"]["token"])
        self.assertEqual(AuthToken.objects.filter(user=self.staff).count(), 1)

    def test_superuser_reset_does_not_issue_target_token(self):
        AuthToken.objects.create(self.other_staff)
        self.client.force_authenticate(user=self.superuser)

        response = self.client.post(
            "/api/v1/administrators/change_password/",
            {
                "email_address": self.other_staff.email_address,
                "new_password": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.other_staff.refresh_from_db()
        self.assertTrue(self.other_staff.check_password(NEW_PASSWORD))
        self.assertIsNone(response.data["response"]["token"])
        self.assertFalse(
            AuthToken.objects.filter(user=self.other_staff).exists()
        )


class TokenInvalidationCommandTests(TestCase):
    def test_command_invalidates_all_tokens(self):
        first = create_administrator("token-first@example.test")
        second = create_administrator("token-second@example.test")
        AuthToken.objects.create(first)
        AuthToken.objects.create(second)
        output = StringIO()

        call_command("invalidate_auth_tokens", "--all", stdout=output)

        self.assertFalse(AuthToken.objects.exists())
        self.assertIn("Invalidated 2 API token(s).", output.getvalue())
