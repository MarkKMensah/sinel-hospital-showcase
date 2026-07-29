from django.test import TestCase
from django.urls import reverse

from accounts.models import Administrator

from .models import Post


class PublicBlogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Administrator.objects.create_user(
            email_address="editor@example.test",
            password=None,
            fullname="Sinel Editor",
            title="Editor",
        )
        cls.visible_post = Post.objects.create(
            title="A practical guide to family health",
            content="<p>Useful, dependable health guidance for families.</p>",
            thumbnail="uploads/images/family-health.jpg",
            tags="Family health, Wellness",
            by=cls.author,
            visible=True,
        )
        cls.hidden_post = Post.objects.create(
            title="Unpublished clinical draft",
            content="<p>This content is not ready for visitors.</p>",
            thumbnail="uploads/images/clinical-draft.jpg",
            tags="Draft",
            by=cls.author,
            visible=False,
        )

    def test_listing_uses_live_dashboard_posts_and_real_search(self):
        response = self.client.get(reverse("blog:posts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.visible_post.title)
        self.assertNotContains(response, self.hidden_post.title)
        self.assertContains(response, 'role="search"')
        self.assertContains(response, "Latest story")

        matching = self.client.get(
            reverse("blog:posts"),
            {"q": "family"},
        )
        no_match = self.client.get(
            reverse("blog:posts"),
            {"q": "orthopaedics"},
        )

        self.assertContains(matching, self.visible_post.title)
        self.assertContains(no_match, "No stories matched your search")

    def test_hidden_post_detail_is_not_publicly_accessible(self):
        response = self.client.get(
            reverse("blog:post_detail", args=[self.hidden_post.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_post_detail_uses_real_title_tags_and_content(self):
        response = self.client.get(
            reverse("blog:post_detail", args=[self.visible_post.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.visible_post.title)
        self.assertContains(response, "Family health")
        self.assertContains(response, "Useful, dependable health guidance")
        self.assertNotContains(
            response,
            "List of Countries without Coronavirus case",
        )
