"""Bounded editorial placement controls; never grant publication to hidden items."""

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from blog.models import Page
from sinel_web.utils.decorators import staff_only
from website.models import Media, Partner, TeamLead
from .editor_state import (
    CONFLICT_MESSAGE, TOKEN_FIELD, editor_instance, locked_editor_instance,
    revision_matches, revision_token,
)


class PlacementForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-check-input" if isinstance(field.widget, forms.CheckboxInput)
                else "form-control"
            )
            if isinstance(field, forms.CharField) and field.max_length:
                field.widget.attrs["maxlength"] = field.max_length
                field.help_text = f"Up to {field.max_length} characters. Plain text."


class TeamPlacementForm(PlacementForm):
    class Meta:
        model = TeamLead
        fields = ("featured", "featured_position")


class PartnerPlacementForm(PlacementForm):
    class Meta:
        model = Partner
        fields = ("featured", "featured_position")


class GalleryPlacementForm(PlacementForm):
    class Meta:
        model = Media
        fields = ("featured", "featured_position", "alternative_text", "credit")


class PagePlacementForm(PlacementForm):
    class Meta:
        model = Page
        fields = ("show_in_header", "show_in_footer", "menu_label", "menu_position")


PLACEMENTS = {
    "team": (TeamLead, TeamPlacementForm, "Team portraits", "fullname", (
        "Choose up to three visible profiles for the Team page introduction. "
        "Lower positions appear first; equal positions use record order. "
        "With no visible selection, the existing automatic selection is used."
    )),
    "partners": (Partner, PartnerPlacementForm, "Featured partners", "name", (
        "Choose up to six visible partners for the Partners page introduction. "
        "All visible partners still appear in the directory and homepage strip. "
        "With no visible selection, the directory order is used."
    )),
    "gallery": (Media, GalleryPlacementForm, "Gallery cover and descriptions", "name", (
        "The first visible featured image becomes the gallery cover. "
        "With no visible selection, the newest visible image is used. "
        "Descriptions and credits apply wherever this gallery image is shown."
    )),
    "pages": (Page, PagePlacementForm, "Page links", "title", (
        "Choose where each visible page is linked. Lower positions appear first. "
        "A visible page can remain accessible without a menu link; hidden pages "
        "are never linked. Blank menu labels use the page title."
    )),
}


def placement_config(kind):
    try:
        return PLACEMENTS[kind]
    except KeyError:
        raise Http404("Content group not found.")


@method_decorator(staff_only(), name="dispatch")
class CurationListView(View):
    def get(self, request, kind):
        model, form_class, title, name_field, guidance = placement_config(kind)
        query = request.GET.get("q", "").strip()[:100]
        records = model.objects.order_by(name_field, "pk")
        if query:
            records = records.filter(Q(**{f"{name_field}__icontains": query}))
        page = Paginator(records, 40).get_page(request.GET.get("page"))
        rows = [{"record": record, "label": getattr(record, name_field)} for record in page]
        return render(request, "dashboard/curation.html", {
            "kind": kind, "title": title, "guidance": guidance,
            "rows": rows, "page_obj": page, "query": query,
            "groups": [(key, item[2]) for key, item in PLACEMENTS.items()],
        })


@method_decorator(staff_only(), name="dispatch")
class CurationEditView(View):
    template_name = "dashboard/curation_edit.html"

    def get(self, request, kind, record_id):
        model, form_class, title, name_field, guidance = placement_config(kind)
        record = editor_instance(model, record_id)
        form = form_class(instance=record)
        return self.show(request, kind, record, form, title, name_field, guidance,
                         revision_token(model, record, form.Meta.fields))

    def post(self, request, kind, record_id):
        model, form_class, title, name_field, guidance = placement_config(kind)
        token = request.POST.get(TOKEN_FIELD, "")
        with locked_editor_instance(model, record_id) as record:
            form = form_class(request.POST, instance=record)
            if not revision_matches(token, model, record, form.Meta.fields):
                form.add_error(None, CONFLICT_MESSAGE)
                return self.show(request, kind, record, form, title, name_field,
                                 guidance, token, status=409)
            if form.is_valid():
                updated = form.save(commit=False)
                updated.save(update_fields=[*form.Meta.fields, "updated_at"])
                messages.success(request, "Display settings saved.")
                return redirect("dashboard:curation", kind=kind)
            return self.show(request, kind, record, form, title, name_field,
                             guidance, token, status=400)

    def show(self, request, kind, record, form, title, name_field, guidance, token, status=200):
        return render(request, self.template_name, {
            "kind": kind, "record": record, "label": getattr(record, name_field),
            "title": title, "guidance": guidance, "form": form,
            "editor_revision": token,
            "reload_url": reverse("dashboard:curation_edit", args=[kind, record.pk]),
        }, status=status)
