from django.contrib import admin
from django.shortcuts import reverse
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from accounts.models import Administrator
from blog.forms import PageForm, PostForm
from blog.models import Page, Post
from website.forms import AboutOverviewForm, ServiceForm
from website.models import About, Service
from website.rich_content import sanitize_rich_html


ATTACK = (
    '<p>Fictional care <strong>information</strong>.</p>'
    '<script>window.evil_marker=1</script>'
    '<iframe src="https://example.test/frame">private frame</iframe>'
    '<img src="/media/fictional.png" onerror="evil_marker()">'
    '<a href="javascript:evil_marker()">Unsafe destination</a>'
)


class RichContentPolicyTests(TestCase):
    def test_preserves_headings_lists_tables_figures_and_inline_formatting(self):
        source = (
            '<h2>Fictional care</h2><p><strong>Bold</strong> <em>emphasis</em>'
            ' <u>underlined</u><sub>2</sub><sup>3</sup><br>next line</p>'
            '<ul><li>First</li></ul><ol start="2"><li>Second</li></ol>'
            '<figure class="image image-style-side"><img src="/media/fictional.jpg" '
            'alt="Fictional exterior" width="600"><figcaption>Caption</figcaption></figure>'
            '<figure class="table"><table><thead><tr><th scope="col">Heading</th>'
            '</tr></thead><tbody><tr><td colspan="2">Cell</td></tr></tbody></table></figure>'
        )
        result = sanitize_rich_html(source)
        for fragment in (
            '<h2>Fictional care</h2>', '<strong>Bold</strong>', '<em>emphasis</em>',
            '<ul><li>First</li></ul>', '<ol start="2">', '<figure class="image image-style-side">',
            'alt="Fictional exterior"', '<figcaption>Caption</figcaption>',
            '<table>', '<th scope="col">Heading</th>', '<td colspan="2">Cell</td>',
        ):
            self.assertIn(fragment, result)

    def test_rejects_executable_tags_events_unsafe_urls_and_html_comments(self):
        result = sanitize_rich_html(ATTACK + '<svg><a onload="evil_marker()">SVG attack</a></svg><!-- hidden -->')
        self.assertIn('<p>Fictional care <strong>information</strong>.</p>', result)
        for marker in ('<script', 'evil_marker', '<iframe', 'private frame', 'onerror', 'javascript:', '<svg', 'SVG attack', '<!--'):
            self.assertNotIn(marker, result)
        self.assertIn('src="/media/fictional.png"', result)

    def test_encoded_and_malformed_payloads_do_not_execute(self):
        attacks = [
            '<a href="jav&#x61;script:alert(1)">x</a>',
            '<a href="java\nscript:alert(1)">x</a>',
            '<img src="data:image/svg+xml;base64,ABC" onerror="alert(1)">',
            '<math><mtext><table><mglyph><style><!--</style><img title="--><img src=x onerror=alert(1)>">',
            '<svg><style><img src=x onerror=alert(1)></style></svg>',
            '<a href="//external.example.test/path">x</a>',
            # Synthetic userinfo tests rejection, not a usable credential.
            '<a href="https://' + 'user:password@example.test">x</a>',
            '<img src="\\evil.example.test/image.png">',
        ]
        for source in attacks:
            with self.subTest(source=source):
                result = sanitize_rich_html(source)
                self.assertNotIn('javascript:', result.lower())
                self.assertNotIn('onerror=', result.lower())
                self.assertNotIn('<script', result.lower())
                self.assertNotIn('<svg', result.lower())
                self.assertNotIn('href="//', result.lower())
                self.assertNotIn('data:image', result.lower())
                self.assertNotIn('user:password', result.lower())

    def test_keeps_only_approved_inline_style_values(self):
        source = (
            '<p style="text-align:center;color:#253170;font-weight:bold;position:fixed;'
            'background-image:url(https://evil.example.test);width:9999px;'
            'z-index:9999;behavior:url(x);font-size:18px">Formatted</p>'
            '<span style="color:expression(alert(1));font-style:italic">Note</span>'
        )
        result = sanitize_rich_html(source)
        for item in ('text-align:center', 'color:#253170', 'font-weight:bold', 'font-size:18px', 'font-style:italic'):
            self.assertIn(item, result)
        for item in ('position', 'url(', 'z-index', 'behavior', '9999', 'expression'):
            self.assertNotIn(item, result)

    def test_ordinary_links_remain_safe_and_sanitization_is_idempotent(self):
        source = (
            '<a href="https://example.test/story" target="_blank">Web</a>'
            '<a href="/services">Services</a><a href="#details">Details</a>'
            '<a href="mailto:fictional@example.test">Email</a><a href="tel:+233000000000">Call</a>'
        )
        result = sanitize_rich_html(source)
        for url in ('https://example.test/story', '/services', '#details', 'mailto:fictional@example.test', 'tel:+233000000000'):
            self.assertIn(url, result)
        self.assertIn('rel="noopener noreferrer"', result)
        self.assertEqual(sanitize_rich_html(result), result)

    def test_filter_sanitizes_before_safe_string_rendering(self):
        rendered = Template('{% load content_safety %}{{ value|rich_content }}').render(Context({'value': ATTACK}))
        self.assertIn('<strong>information</strong>', rendered)
        self.assertNotIn('evil_marker', rendered)


class RichContentBoundaryTests(TestCase):
    def setUp(self):
        self.editor = Administrator.objects.create_user(
            email_address="rich.editor@example.test", password="fictional-local-only",
            fullname="Fictional Rich Editor", is_staff=True, is_superuser=True,
        )
        self.about = About.objects.create(overview="<p>Overview</p>", mission="<p>Mission</p>", vision="<p>Vision</p>", value="<p>Values</p>")
        self.service = Service.objects.create(title="Fictional care", description="<p>Care</p>", schedules="<p>Daily</p>", image="fictional.jpg", visible=True)
        self.post = Post.objects.create(title="Fictional article", content="<p>News</p>", thumbnail="fictional.jpg", tags="fictional", by=self.editor, visible=True)
        self.page = Page.objects.create(title="Fictional page", content="<p>Page</p>", by=self.editor, visible=True)

    def test_model_saves_sanitize_all_rich_fields(self):
        for instance, fields in [
            (self.about, ('overview', 'mission', 'vision', 'value')),
            (self.service, ('description', 'schedules')),
            (self.post, ('content',)), (self.page, ('content',)),
        ]:
            for name in fields:
                setattr(instance, name, ATTACK)
            instance.save()
            instance.refresh_from_db()
            for name in fields:
                self.assertNotIn('evil_marker', getattr(instance, name))
                self.assertIn('<strong>information</strong>', getattr(instance, name))

    def test_partial_save_does_not_rewrite_unrelated_legacy_fields(self):
        About.objects.filter(pk=self.about.pk).update(overview=ATTACK, mission=ATTACK)
        self.about.refresh_from_db()
        self.about.overview = ATTACK
        self.about.save(update_fields=['overview'])
        raw = About.objects.filter(pk=self.about.pk).values('overview', 'mission').get()
        self.assertNotIn('evil_marker', raw['overview'])
        self.assertEqual(raw['mission'], ATTACK)

    def test_legacy_public_and_dashboard_reads_are_safe_without_database_rewrite(self):
        About.objects.filter(pk=self.about.pk).update(overview=ATTACK, mission=ATTACK, vision=ATTACK, value=ATTACK)
        Service.objects.filter(pk=self.service.pk).update(description=ATTACK, schedules=ATTACK)
        Post.objects.filter(pk=self.post.pk).update(content=ATTACK)
        Page.objects.filter(pk=self.page.pk).update(content=ATTACK)
        self.client.force_login(self.editor)
        routes = [
            reverse('website:index'), reverse('website:about'),
            reverse('website:service_details', args=[self.service.pk]),
            reverse('blog:post_detail', args=[self.post.pk]),
            reverse('website:static_page_view', args=[self.page.pk, self.page.slug]),
            reverse('dashboard:index'),
        ]
        for path in routes:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'evil_marker')
                self.assertContains(response, '<strong>information</strong>')
        self.assertEqual(About.objects.values_list('overview', flat=True).get(pk=self.about.pk), ATTACK)
        self.assertEqual(Post.objects.values_list('content', flat=True).get(pk=self.post.pk), ATTACK)

    def test_editor_initial_values_are_safe_but_instance_fingerprint_stays_raw(self):
        for instance, field, form_class in [
            (self.about, 'overview', AboutOverviewForm),
            (self.service, 'description', ServiceForm),
            (self.post, 'content', PostForm),
            (self.page, 'content', PageForm),
        ]:
            setattr(instance, field, ATTACK)
            form = form_class(instance=instance)
            self.assertNotIn('evil_marker', form.initial[field])
            self.assertEqual(getattr(form.instance, field), ATTACK)
            self.assertIn('<strong>information</strong>', form.initial[field])

    def test_rejected_bound_editor_retains_safe_rich_formatting(self):
        form = PostForm({'title': '', 'content': ATTACK, 'tags': 'fictional'}, instance=self.post)
        self.assertFalse(form.is_valid())
        self.assertNotIn('evil_marker', form['content'].value())
        self.assertIn('<strong>information</strong>', form['content'].value())
        self.assertIn('title', form.errors)

    def test_django_admin_legacy_initial_uses_same_sanitizer(self):
        self.about.overview = ATTACK
        request = RequestFactory().get('/admin/website/about/')
        request.user = self.editor
        form_class = admin.site._registry[About].get_form(request, self.about)
        form = form_class(instance=self.about)
        self.assertNotIn('evil_marker', form.initial['overview'])
        self.assertEqual(form.instance.overview, ATTACK)

    def test_legacy_edit_save_keeps_revision_checks_valid(self):
        About.objects.filter(pk=self.about.pk).update(overview=ATTACK)
        Post.objects.filter(pk=self.post.pk).update(content=ATTACK)
        self.client.force_login(self.editor)
        about_url = reverse('dashboard:about')
        response = self.client.get(about_url + '?section=overview')
        form = response.context['overview_form']
        self.assertNotContains(response, 'evil_marker')
        response = self.client.post(about_url, {
            'section': 'overview', 'overview': form.initial['overview'],
            'editor_revision': form.editor_revision,
        })
        self.assertEqual(response.status_code, 302)
        post_url = reverse('dashboard:create_update_post')
        response = self.client.get(post_url, {'post_id': self.post.pk})
        form = response.context['form']
        self.assertNotContains(response, 'evil_marker')
        response = self.client.post(post_url, {
            'post_id': self.post.pk, 'editor_revision': response.context['editor_revision'],
            'title': self.post.title, 'content': form.initial['content'],
            'tags': 'fictional', 'visible': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.about.refresh_from_db()
        self.post.refresh_from_db()
        self.assertNotIn('evil_marker', self.about.overview)
        self.assertNotIn('evil_marker', self.post.content)
