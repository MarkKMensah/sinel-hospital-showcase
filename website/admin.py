from django.contrib import admin
from django import forms
from .rich_content import RichContentFormMixin

from .models import (
    About,
    Award,
    Banner,
    Client,
    Contact,
    HealthTips,
    HomepageShortcut,
    HomepageVideo,
    InsurancePartner,
    Media,
    OpeningHour,
    Service,
    SocialMediaLink,
    TeamLead,
)


admin.site.register(
    (
        Award,
        Banner,
        Client,
        Contact,
        HealthTips,
        HomepageShortcut,
        HomepageVideo,
        InsurancePartner,
        Media,
        OpeningHour,
        SocialMediaLink,
        TeamLead,
    )
)


class RichContentAdminForm(RichContentFormMixin, forms.ModelForm):
    class Meta:
        fields = "__all__"


@admin.register(About, Service)
class RichContentAdmin(admin.ModelAdmin):
    form = RichContentAdminForm
