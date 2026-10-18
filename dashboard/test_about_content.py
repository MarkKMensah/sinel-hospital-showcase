from django import forms
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils.html import escape
from rest_framework.test import APIClient

from accounts.models import Administrator
from website.forms import (
    AboutForm,
    AboutHeroForm,
    AboutMissionForm,
    AboutOverviewForm,
    AboutValueForm,
    AboutVisionForm,
)
from website.models import About


HERO_LIMITS = {
    "hero_title": 80,
    "hero_description": 240,
    "years_value": 12,
    "years_label": 40,
    "availability_value": 12,
    "availability_label": 40,
    "hero_note": 100,
}
HERO_COPY = {
    "hero_title": "Specialist care for every generation",
    "hero_description": "Hospital-managed introduction for patients everywhere.",
    "years_value": "41+",
    "years_label": "Years of dedicated care",
    "availability_value": "Every day",
    "availability_label": "Here when you need us",
    "hero_note": "Personal care for local and international visitors.",
}
RICH_COPY = {
    "overview": "<h2>Original overview</h2>",
    "mission": "<p>Original mission</p>",
    "vision": "<p>Original vision</p>",
    "value": "<p>Original values</p>",
}


def staff_user(label, role=Administrator.Role.CONTENT_MANAGER, active=True):
    return Administrator.objects.create_user(
        email_address=f"about-{label}@example.test",
        password=None,
        fullname=label,
        is_staff=True,
        is_active=active,
        role=role,
    )


class AboutHeroFormTests(SimpleTestCase):
    def test_defaults_and_seven_field_limits_are_stable(self):
        self.assertEqual(set(About.HERO_DEFAULTS), set(HERO_LIMITS))
        about = About()
        for name, limit in HERO_LIMITS.items():
            with self.subTest(field=name):
                self.assertEqual(About._meta.get_field(name).max_length, limit)
                self.assertEqual(getattr(about, name), About.HERO_DEFAULTS[name])
                self.assertTrue(getattr(about, name))
                self.assertLessEqual(len(getattr(about, name)), limit)

    def test_fields_are_required_plain_text_with_limits_and_counter_help(self):
        form = AboutHeroForm()
        self.assertEqual(list(form.fields), list(HERO_LIMITS))
        for name, limit in HERO_LIMITS.items():
            with self.subTest(field=name):
                field = form.fields[name]
                self.assertIsInstance(field, forms.CharField)
                self.assertIsInstance(field.widget, (forms.TextInput, forms.Textarea))
                self.assertTrue(field.required)
                self.assertEqual(field.max_length, limit)
                self.assertEqual(field.widget.attrs["maxlength"], limit)
                self.assertEqual(field.widget.attrs["data-about-character-limit"], limit)
                described_by = field.widget.attrs["aria-describedby"].split()
                self.assertIn(f"id_{name}_help", described_by)
                self.assertIn(f"id_{name}_count", described_by)
                self.assertIn(str(limit), field.help_text)
                self.assertIn("Plain text", field.help_text)
                self.assertIn(f'maxlength="{limit}"', str(form[name]))

    def test_each_field_accepts_exact_limit_and_rejects_one_character_over(self):
        for name, limit in HERO_LIMITS.items():
            for length in (1, limit, limit + 1):
                with self.subTest(field=name, length=length):
                    form = AboutHeroForm({**HERO_COPY, name: "X" * length})
                    self.assertEqual(form.is_valid(), length <= limit, form.errors)
                    if length > limit:
                        self.assertIn(name, form.errors)

    def test_missing_blank_and_whitespace_only_fields_are_rejected(self):
        for name in HERO_LIMITS:
            for value in (None, "", " \t\n "):
                with self.subTest(field=name, value=value):
                    payload = dict(HERO_COPY)
                    if value is None:
                        del payload[name]
                    else:
                        payload[name] = value
                    form = AboutHeroForm(payload)
                    self.assertFalse(form.is_valid())
                    self.assertIn(name, form.errors)

    def test_legacy_form_removes_only_omitted_introduction_fields(self):
        form = AboutForm(RICH_COPY, instance=About(**HERO_COPY))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(set(HERO_LIMITS).intersection(form.fields))
        partial = AboutForm(
            {**RICH_COPY, "hero_title": "A supplied heading"},
            instance=About(**HERO_COPY),
        )
        self.assertTrue(partial.is_valid(), partial.errors)
        self.assertIn("hero_title", partial.fields)
        self.assertNotIn("hero_description", partial.fields)


class AboutContentDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.about = About.objects.create(**RICH_COPY, **HERO_COPY)
        cls.manager = staff_user("manager")
        cls.auditor = staff_user("auditor", Administrator.Role.AUDITOR)
        cls.front_desk = staff_user("front-desk", Administrator.Role.FRONT_DESK)
        cls.inactive = staff_user("inactive", active=False)

    def setUp(self):
        self.client.force_login(self.manager)
        self.url = reverse("dashboard:about")

    def state(self):
        return list(About.objects.order_by("pk").values())

    def post_section(self, payload, **kwargs):
        section = payload["section"]
        editor = self.client.get(self.url, {"section": section})
        token = editor.context[f"{section}_form"].editor_revision
        return self.client.post(self.url, {**payload, "editor_revision": token}, **kwargs)

    def test_manager_can_save_only_introduction_fields_with_success_notice(self):
        changes = {**HERO_COPY, "hero_title": "Updated by the hospital team"}
        response = self.post_section(
            {"section": "hero", **changes, **dict.fromkeys(RICH_COPY, "Do not save")},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page introduction updated successfully.")
        self.about.refresh_from_db()
        for name, value in changes.items():
            self.assertEqual(getattr(self.about, name), value)
        for name, value in RICH_COPY.items():
            self.assertEqual(getattr(self.about, name), value)
        self.assertContains(
            self.client.get(reverse("website:about")), changes["hero_title"]
        )

    def test_overlong_submissions_return_400_retain_input_and_do_not_write(self):
        original = self.state()
        for name, limit in HERO_LIMITS.items():
            with self.subTest(field=name):
                payload = {"section": "hero", **HERO_COPY, name: "X" * (limit + 1)}
                response = self.post_section(payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.context["active_section"], "hero")
                self.assertIn(name, response.context["hero_form"].errors)
                self.assertEqual(response.context["hero_form"][name].value(), payload[name])
                self.assertContains(response, payload[name], status_code=400)
                self.assertEqual(self.state(), original)

    def test_empty_database_gets_do_not_write_and_valid_post_creates_first_record(self):
        About.objects.all().delete()
        for url in (self.url, reverse("website:about")):
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(About.objects.count(), 0)
        response = self.post_section({"section": "hero", **HERO_COPY})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(About.objects.count(), 1)
        created = About.objects.get()
        for name, value in HERO_COPY.items():
            self.assertEqual(getattr(created, name), value)
        for name in RICH_COPY:
            self.assertEqual(getattr(created, name), "")

    def test_invalid_first_submission_does_not_create_record(self):
        About.objects.all().delete()
        response = self.post_section({"section": "hero", **HERO_COPY, "hero_title": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("hero_title", response.context["hero_form"].errors)
        self.assertEqual(About.objects.count(), 0)

    def test_auditor_front_desk_inactive_and_anonymous_cannot_change_content(self):
        original = self.state()
        cases = (
            (self.auditor, 200, 403),
            (self.front_desk, 403, 403),
            (self.inactive, 302, 302),
            (None, 302, 302),
        )
        for user, read_status, write_status in cases:
            with self.subTest(user=user):
                self.client.logout()
                if user is not None:
                    self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, read_status)
                response = self.client.post(
                    self.url,
                    {"section": "hero", **HERO_COPY, "hero_title": "Not authorised"},
                )
                self.assertEqual(response.status_code, write_status)
                self.assertEqual(self.state(), original)

    def test_legacy_section_edits_do_not_overwrite_introduction_or_other_sections(self):
        for section in RICH_COPY:
            with self.subTest(section=section):
                original = self.state()[0]
                replacement = f"<p>Updated {section}</p>"
                response = self.post_section(
                    {"section": section, section: replacement, "hero_title": "Ignore me"},
                )
                self.assertEqual(response.status_code, 302)
                self.about.refresh_from_db()
                self.assertEqual(getattr(self.about, section), replacement)
                for name in HERO_LIMITS:
                    self.assertEqual(getattr(self.about, name), original[name])
                for name in set(RICH_COPY) - {section}:
                    self.assertEqual(getattr(self.about, name), original[name])

    def test_dashboard_renders_all_field_help_and_character_counters(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="section" value="hero"')
        for name, limit in HERO_LIMITS.items():
            self.assertContains(response, f'id="id_{name}_help"')
            self.assertContains(response, f'id="id_{name}_count"')
            self.assertContains(response, f'data-about-character-count="id_{name}"')
            self.assertContains(response, f'data-about-character-limit="{limit}"')


class AboutIntroductionPublicTests(TestCase):
    def test_empty_database_uses_defaults_without_creating_an_about_record(self):
        response = self.client.get(reverse("website:about"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["about"])
        self.assertIsNone(response.context["about_hero"].pk)
        for value in About.HERO_DEFAULTS.values():
            self.assertContains(response, escape(value))
        self.assertContains(response, "Our story is being updated")
        self.assertEqual(About.objects.count(), 0)

    def test_saved_plain_copy_is_escaped_while_legacy_rich_sections_keep_formatting(self):
        copy = {
            "hero_title": '<script>alert("heading")</script> & care',
            "hero_description": '<img src=x onerror="alert(1)"> & personalised care',
            "years_value": "<b>41+</b>",
            "years_label": "<b>Care experience</b>",
            "availability_value": "<i>24/7</i>",
            "availability_label": "<i>Care availability</i>",
            "hero_note": '<script>alert("note")</script> & welcome',
        }
        About.objects.create(**copy, **RICH_COPY)
        response = self.client.get(reverse("website:about"))
        for value in copy.values():
            self.assertContains(response, escape(value))
            self.assertNotContains(response, value)
        for value in RICH_COPY.values():
            self.assertContains(response, value, html=True)


class AboutLegacyApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.about = About.objects.create(**RICH_COPY, **HERO_COPY)
        cls.manager = staff_user("api-manager")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.manager)
        self.url = "/api/v1/about"

    def state(self):
        return list(About.objects.order_by("pk").values())

    def test_legacy_put_without_introduction_fields_keeps_saved_copy(self):
        changes = {name: f"<p>API {name}</p>" for name in RICH_COPY}
        response = self.client.put(self.url, changes, format="json")
        self.assertEqual(response.status_code, 200)
        self.about.refresh_from_db()
        for name, value in HERO_COPY.items():
            self.assertEqual(getattr(self.about, name), value)
            self.assertEqual(response.data["about"][name], value)
        for name, value in changes.items():
            self.assertEqual(getattr(self.about, name), value)

    def test_legacy_first_put_creates_about_with_introduction_defaults(self):
        About.objects.all().delete()
        response = self.client.put(self.url, RICH_COPY, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(About.objects.count(), 1)
        created = About.objects.get()
        for name, value in About.HERO_DEFAULTS.items():
            self.assertEqual(getattr(created, name), value)
            self.assertEqual(response.data["about"][name], value)

    def test_supplied_valid_field_updates_without_resetting_omitted_fields(self):
        response = self.client.put(
            self.url, {**RICH_COPY, "hero_title": "API-managed introduction"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.about.refresh_from_db()
        self.assertEqual(self.about.hero_title, "API-managed introduction")
        for name in set(HERO_COPY) - {"hero_title"}:
            self.assertEqual(getattr(self.about, name), HERO_COPY[name])

    def test_supplied_overlong_or_blank_fields_return_400_without_writes(self):
        original = self.state()
        for name, limit in HERO_LIMITS.items():
            for value in ("X" * (limit + 1), "", " \t "):
                with self.subTest(field=name, length=len(value)):
                    response = self.client.put(
                        self.url, {**RICH_COPY, name: value}, format="json"
                    )
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(name, str(response.data))
                    self.assertEqual(self.state(), original)

    def test_api_permissions_block_auditor_front_desk_inactive_and_anonymous(self):
        original = self.state()
        forbidden = (
            staff_user("api-auditor", Administrator.Role.AUDITOR),
            staff_user("api-front-desk", Administrator.Role.FRONT_DESK),
            staff_user("api-inactive", active=False),
            None,
        )
        for user in forbidden:
            with self.subTest(user=user):
                self.client.force_authenticate(user)
                response = self.client.put(
                    self.url, {**RICH_COPY, "hero_title": "Forbidden"}, format="json"
                )
                self.assertIn(response.status_code, (401, 403))
                self.assertEqual(self.state(), original)


class AboutConcurrentSaveTests(TestCase):
    rich_forms = {
        "overview": AboutOverviewForm,
        "mission": AboutMissionForm,
        "vision": AboutVisionForm,
        "value": AboutValueForm,
    }

    @classmethod
    def setUpTestData(cls):
        cls.about = About.objects.create(**RICH_COPY, **HERO_COPY)

    def form_cases(self):
        return (
            (AboutHeroForm, {**HERO_COPY, "hero_title": "New introduction"}),
            (AboutForm, {**RICH_COPY, "hero_title": "Legacy API introduction"}),
            *(
                (form_class, {name: f"<p>New {name}</p>"})
                for name, form_class in self.rich_forms.items()
            ),
        )

    def test_stale_hero_save_preserves_all_concurrent_rich_section_edits(self):
        payload = {**HERO_COPY, "hero_title": "Updated introduction"}
        form = AboutHeroForm(payload, instance=About.objects.get(pk=self.about.pk))
        self.assertTrue(form.is_valid(), form.errors)
        concurrent = {name: f"<p>Concurrent {name}</p>" for name in RICH_COPY}
        About.objects.filter(pk=self.about.pk).update(**concurrent)

        form.save()

        self.about.refresh_from_db()
        for name, value in payload.items():
            self.assertEqual(getattr(self.about, name), value)
        for name, value in concurrent.items():
            self.assertEqual(getattr(self.about, name), value)

    def test_each_stale_rich_section_save_preserves_concurrent_introduction(self):
        for section, form_class in self.rich_forms.items():
            with self.subTest(section=section):
                stale = About.objects.get(pk=self.about.pk)
                original_rich = {name: getattr(stale, name) for name in RICH_COPY}
                replacement = f"<p>Edited {section}</p>"
                form = form_class({section: replacement}, instance=stale)
                self.assertTrue(form.is_valid(), form.errors)
                concurrent = {
                    **HERO_COPY,
                    "hero_title": f"Introduction changed while editing {section}",
                }
                About.objects.filter(pk=self.about.pk).update(**concurrent)

                form.save()

                self.about.refresh_from_db()
                self.assertEqual(getattr(self.about, section), replacement)
                for name, value in concurrent.items():
                    self.assertEqual(getattr(self.about, name), value)
                for name in set(RICH_COPY) - {section}:
                    self.assertEqual(getattr(self.about, name), original_rich[name])

    def test_stale_legacy_form_updates_supplied_hero_without_resetting_omitted_copy(self):
        form = AboutForm(
            {**RICH_COPY, "hero_title": "Heading supplied by the API"},
            instance=About.objects.get(pk=self.about.pk),
        )
        self.assertTrue(form.is_valid(), form.errors)
        concurrent = {
            **HERO_COPY,
            "hero_title": "Concurrent heading",
            "hero_description": "Concurrent supporting text",
            "hero_note": "Concurrent summary note",
        }
        About.objects.filter(pk=self.about.pk).update(**concurrent)

        form.save()

        self.about.refresh_from_db()
        self.assertEqual(self.about.hero_title, "Heading supplied by the API")
        for name in set(HERO_LIMITS) - {"hero_title"}:
            self.assertEqual(getattr(self.about, name), concurrent[name])

    def test_each_content_form_can_save_a_new_record_with_omitted_defaults(self):
        for form_class, payload in self.form_cases():
            with self.subTest(form=form_class.__name__):
                count = About.objects.count()
                form = form_class(payload)
                self.assertTrue(form.is_valid(), form.errors)

                saved = form.save()

                self.assertIsNotNone(saved.pk)
                self.assertEqual(About.objects.count(), count + 1)
                saved.refresh_from_db()
                self.assertIsNotNone(saved.created_at)
                self.assertIsNotNone(saved.updated_at)
                for name, value in payload.items():
                    self.assertEqual(getattr(saved, name), value)
                for name in set(HERO_LIMITS) - set(payload):
                    self.assertEqual(getattr(saved, name), About.HERO_DEFAULTS[name])

    def test_commit_false_leaves_existing_and_new_records_unsaved(self):
        for form_class, payload in self.form_cases():
            for existing in (True, False):
                with self.subTest(form=form_class.__name__, existing=existing):
                    instance = About.objects.get(pk=self.about.pk) if existing else None
                    original = list(About.objects.order_by("pk").values())
                    form = form_class(payload, instance=instance)
                    self.assertTrue(form.is_valid(), form.errors)

                    unsaved = form.save(commit=False)

                    self.assertEqual(
                        list(About.objects.order_by("pk").values()), original
                    )
                    self.assertEqual(unsaved.pk, self.about.pk if existing else None)
                    for name, value in payload.items():
                        self.assertEqual(getattr(unsaved, name), value)
                    self.assertTrue(callable(form.save_m2m))
