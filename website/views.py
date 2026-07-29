from django.shortcuts import get_object_or_404, render
from django.views.generic import View
from blog.models import Page, Post
from .models import (
    About,
    Award,
    Banner,
    HomepageShortcut,
    HomepageVideo,
    Media,
    Partner,
    Service,
    TeamLead,
)


def visible_partners():
    return Partner.objects.filter(visible=True).order_by("category", "name")


class IndexView(View):
    template_name = "website/index.html"

    def get(self, request, *args, **kwargs):
        context = {
            "hero": (
                Banner.objects.filter(visible=True)
                .select_related("service")
                .first()
            ),
            "homepage_shortcuts": (
                HomepageShortcut.objects.filter(
                    visible=True,
                    service__visible=True,
                )
                .select_related("service")
                .order_by("position", "id")
            ),
            "about": About.objects.first(),
            "homepage_video": HomepageVideo.objects.filter(
                visible=True
            ).first(),
            "visible_service_count": Service.objects.filter(
                visible=True
            ).count(),
            "partners": visible_partners(),
            "team": TeamLead.objects.filter(visible=True).order_by(
                "updated_at"
            ),
            "posts": Post.objects.filter(visible=True).order_by("-id")[:5],
        }
        return render(request, self.template_name, context)


class AboutView(View):
    template_name = "website/about.html"

    def get(self, request, *args, **kwargs):
        context = {
            "about": About.objects.first(),
            "awards": [
                award
                for award in Award.objects.filter(visible=True)
                if award.display_image_url
            ],
        }
        return render(request, self.template_name, context)


class ContactView(View):
    template_name = "website/contact.html"

    def get(self, request, *args, **kwargs):
        context = {}

        return render(request, self.template_name, context)


class GalleryView(View):
    template_name = "website/gallery.html"

    def get(self, request, *args, **kwargs):
        context = {
            "media": Media.objects.filter(visible=True).order_by("-id"),
        }

        return render(request, self.template_name, context)


class ServicesView(View):
    template_name = "website/services.html"

    def get(self, request, *args, **kwargs):
        context = {
            "services": Service.objects.filter(visible=True).order_by("title")
        }
        return render(request, self.template_name, context)


class DoctorsView(View):
    template_name = "website/team.html"

    def get(self, request, *args, **kwargs):
        team_leads = sorted(
            TeamLead.objects.filter(visible=True),
            key=lambda member: (
                member.title.casefold(),
                member.fullname.casefold(),
            ),
        )
        specialities = list(
            dict.fromkeys(member.title for member in team_leads)
        )
        hero_members = sorted(
            team_leads,
            key=lambda member: (
                0 if "mccarthy" in member.fullname.casefold() else 1,
                member.title.casefold(),
                member.fullname.casefold(),
            ),
        )[:3]
        context = {
            "doctors": team_leads,
            "hero_members": hero_members,
            "specialities": specialities,
        }
        return render(request, self.template_name, context)


class OurPatnersView(View):
    template_name = "website/our_partners.html"

    def get(self, request, *args, **kwargs):
        partners = list(visible_partners())
        categories = list(
            dict.fromkeys(partner.category for partner in partners)
        )
        context = {
            "categories": categories,
            "partners": partners,
        }
        return render(request, self.template_name, context)


class ServiceDetailsView(View):
    template_name = "website/service_details.html"

    def get(self, request, service_id, *args, **kwargs):
        service = get_object_or_404(
            Service,
            id=service_id,
            visible=True,
        )
        doctors = service.doctors.filter(visible=True)
        testimonials = service.testimonials.filter(visible=True)
        context = {
            "service": service,
            "doctors": doctors,
            "testimonials": testimonials,
        }
        return render(request, self.template_name, context)


class StaticPageView(View):
    template_name = "website/static_page.html"

    def get(self, request, page_id, *args, **kwargs):
        page = get_object_or_404(Page, id=page_id)
        context = {
            "page": page,
        }
        return render(request, self.template_name, context)
