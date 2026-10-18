"""Named copy editors with scoped saves and stale-form protection."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from sinel_web.utils.decorators import staff_only
from website.page_content import (
    ContentConflict, METADATA_ROUTES, SECTION_REGISTRY, PageMetadata,
    PageMetadataForm, PageSection, PageSectionForm, save_editor_form,
)


def check_content_access(request, write=False):
    capability = "can_manage_content" if write else "can_view_content"
    if not getattr(request.user, capability, False):
        raise PermissionDenied


def connect_field_descriptions(form):
    """Field guidance and counters remain associated without JavaScript."""
    for field in form.visible_fields():
        descriptions = []
        if field.help_text:
            descriptions.append(f"{field.auto_id}_helptext")
        if getattr(field.field, "max_length", None):
            descriptions.append(f"{field.auto_id}_count")
        if field.errors:
            descriptions.append(f"{field.auto_id}_error")
            field.field.widget.attrs["aria-invalid"] = "true"
        if descriptions:
            field.field.widget.attrs["aria-describedby"] = " ".join(descriptions)


@method_decorator(staff_only(), name="dispatch")
class PageContentListView(View):
    def get(self, request):
        check_content_access(request)
        rows = {row.key: row for row in PageSection.objects.filter(key__in=SECTION_REGISTRY)}
        groups = {}
        for key, spec in SECTION_REGISTRY.items():
            row = rows.get(key)
            groups.setdefault(spec.group, []).append({
                "key": key, "label": spec.label,
                "title": row.title if row else spec.title,
                "updated_at": row.updated_at if row else None,
            })
        return render(request, "dashboard/page_content.html", {"groups": groups})


@method_decorator(staff_only(), name="dispatch")
class PageContentEditView(View):
    def record(self, section_key):
        spec = SECTION_REGISTRY.get(section_key)
        if spec is None:
            raise Http404
        row = PageSection.objects.filter(key=section_key).first()
        if row is None:
            row = PageSection(key=section_key, eyebrow=spec.eyebrow, title=spec.title, body=spec.body)
        return spec, row

    def response(self, request, spec, form, status=200):
        connect_field_descriptions(form)
        return render(request, "dashboard/page_content_edit.html", {
            "heading": spec.label, "group": spec.group, "form": form,
            "return_route": "dashboard:page_content",
            "can_edit": request.user.can_manage_content,
        }, status=status)

    def get(self, request, section_key):
        check_content_access(request)
        spec, record = self.record(section_key)
        form = PageSectionForm(section_key=section_key, instance=record)
        return self.response(request, spec, form)

    def post(self, request, section_key):
        check_content_access(request, write=True)
        spec, record = self.record(section_key)
        form = PageSectionForm(request.POST, request.FILES, section_key=section_key, instance=record)
        if not form.is_valid():
            return self.response(request, spec, form, status=400)
        try:
            save_editor_form(form, "section", section_key)
        except ContentConflict as exc:
            form.add_error(None, str(exc))
            return self.response(request, spec, form, status=409)
        except OSError:
            form.add_error(None, "The image could not be saved. Your text is below; choose the image again and retry.")
            return self.response(request, spec, form, status=503)
        messages.success(request, f"{spec.label} updated successfully.")
        return redirect("dashboard:page_content_edit", section_key=section_key)


@method_decorator(staff_only(), name="dispatch")
class PageMetadataListView(View):
    def get(self, request):
        check_content_access(request)
        records = {row.key: row for row in PageMetadata.objects.filter(key__in=METADATA_ROUTES)}
        pages = [{"key": key, "label": details[0], "record": records.get(key)} for key, details in METADATA_ROUTES.items()]
        return render(request, "dashboard/page_content_metadata.html", {"pages": pages})


@method_decorator(staff_only(), name="dispatch")
class PageMetadataEditView(View):
    def record(self, page_key):
        details = METADATA_ROUTES.get(page_key)
        if details is None:
            raise Http404
        return details[0], PageMetadata.objects.filter(key=page_key).first() or PageMetadata(key=page_key)

    def response(self, request, label, form, status=200):
        connect_field_descriptions(form)
        return render(request, "dashboard/page_content_edit.html", {
            "heading": label, "group": "Search and sharing", "form": form,
            "return_route": "dashboard:page_metadata", "metadata": True,
            "can_edit": request.user.can_manage_content,
        }, status=status)

    def get(self, request, page_key):
        check_content_access(request)
        label, record = self.record(page_key)
        return self.response(request, label, PageMetadataForm(page_key=page_key, instance=record))

    def post(self, request, page_key):
        check_content_access(request, write=True)
        label, record = self.record(page_key)
        form = PageMetadataForm(request.POST, page_key=page_key, instance=record)
        if not form.is_valid():
            return self.response(request, label, form, status=400)
        try:
            save_editor_form(form, "metadata", page_key)
        except ContentConflict as exc:
            form.add_error(None, str(exc))
            return self.response(request, label, form, status=409)
        messages.success(request, "Search and sharing information updated successfully.")
        return redirect("dashboard:page_metadata_edit", page_key=page_key)
