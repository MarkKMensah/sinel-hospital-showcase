"""Real PostgreSQL interleavings; SQLite cannot establish row-lock guarantees."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.contenttypes.models import ContentType
from django.db import close_old_connections, connection
from django.test import Client, TransactionTestCase
from django.urls import reverse

from accounts.models import Administrator
from website.models import Contact, Partner
from website.page_content import PageSection, PageSectionForm


@skipUnless(connection.vendor == "postgresql", "Requires the isolated PostgreSQL CI service")
class EditorialConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = Administrator.objects.create_user(
            email_address="concurrency@example.test", fullname="Fictional editor",
            password=None, is_staff=True, is_active=True,
            role=Administrator.Role.CONTENT_MANAGER,
        )

    def parallel_posts(self, url, payloads):
        # Create sessions before coordinating the competing business requests.
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(self.user)
        barrier = Barrier(2, timeout=15)

        def submit(pair):
            client, payload = pair
            close_old_connections()
            try:
                barrier.wait()
                return client.post(url, payload).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return sorted(pool.map(submit, zip(clients, payloads)))

    def test_two_partner_edits_accept_one_and_reject_stale_other(self):
        partner = Partner.objects.create(
            name="Fictional partner", logo="uploads/fictional.png", category="Insurance Partners",
            website="https://example.test/partner", description="Keep this description", visible=True,
        )
        client = Client()
        client.force_login(self.user)
        url = reverse("dashboard:create_update_partner")
        token = client.get(url, {"partner_id": partner.pk}).context["editor_revision"]
        original = {
            "partner_id": partner.pk, "editor_revision": token, "category": partner.category,
            "description": partner.description, "website": partner.website, "visible": "on",
        }
        statuses = self.parallel_posts(url, [{**original, "name": "First fictional edit"}, {**original, "name": "Second fictional edit"}])
        self.assertEqual(statuses, [302, 409])
        partner.refresh_from_db()
        self.assertIn(partner.name, {"First fictional edit", "Second fictional edit"})
        self.assertEqual(partner.website, original["website"])
        self.assertEqual(partner.description, original["description"])

    def test_two_initial_contact_saves_create_only_one(self):
        ContentType.objects.get_for_model(Contact)
        client = Client()
        client.force_login(self.user)
        url = reverse("dashboard:contact")
        token = client.get(url).context["editor_revision"]
        original = {"editor_revision": token, "email": "care@example.test", "telephone": "+233201234567", "gps": "", "lat_lng": ""}
        self.assertEqual(self.parallel_posts(url, [{**original, "address": "Fictional address one"}, {**original, "address": "Fictional address two"}]), [302, 409])
        self.assertEqual(Contact.objects.count(), 1)

    def test_unique_section_first_save_is_compare_and_insert(self):
        key = "home_services"
        form = PageSectionForm(section_key=key, instance=PageSection(key=key))
        token = form["revision_token"].value()
        original = {"revision_token": token, "eyebrow": "Care", "body": "Fictional care information."}
        url = reverse("dashboard:page_content_edit", args=[key])
        self.assertEqual(self.parallel_posts(url, [{**original, "title": "First fictional section"}, {**original, "title": "Second fictional section"}]), [302, 409])
        self.assertEqual(PageSection.objects.filter(key=key).count(), 1)
