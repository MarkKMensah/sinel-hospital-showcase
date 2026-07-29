from django.contrib import admin

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
)
