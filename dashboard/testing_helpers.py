"""Exercise the same revision handshake as a dashboard browser in tests."""

from django.urls import reverse


def post_editor(client, url, data=None, **kwargs):
    data = dict(data or {})
    for route, identifier in (
        ("create_update_service", "service_id"),
        ("create_update_team_lead", "team_lead_id"),
        ("create_update_banner", "banner_id"),
        ("create_update_homepage_shortcut", "shortcut_id"),
        ("create_update_homepage_video", "homepage_video_id"),
        ("create_update_award", "award_id"),
        ("create_update_album", "album_id"),
        ("create_update_partner", "partner_id"),
        ("create_update_testimonial", "testimonial_id"),
        ("create_update_post", "post_id"),
        ("create_update_page", "page_id"),
        ("create_update_notification", "notification_id"),
        ("create_update_media", "media_id"),
        ("contact", "contact_id"),
    ):
        if url == reverse(f"dashboard:{route}"):
            if "editor_revision" not in data:
                response = client.get(url, {identifier: data[identifier]} if data.get(identifier) else {})
                if response.status_code == 200:
                    data["editor_revision"] = response.context["editor_revision"]
            break
    return client.post(url, data, **kwargs)
