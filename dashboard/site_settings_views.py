from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from sinel_web.utils.decorators import staff_only
from website.site_settings import SiteSettings, SiteSettingsForm, StaleSiteSettings


@method_decorator(staff_only(), name="dispatch")
class SiteSettingsView(View):
    template_name = "dashboard/site_settings.html"

    def dispatch(self, request, *args, **kwargs):
        allowed = (
            request.user.can_view_content
            if request.method in {"GET", "HEAD", "OPTIONS"}
            else request.user.can_manage_content
        )
        if not allowed:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        instance = SiteSettings.objects.filter(pk=1).first() or SiteSettings()
        return render(request, self.template_name, {"settings_form": SiteSettingsForm(instance=instance)})

    def post(self, request):
        instance = SiteSettings.objects.filter(pk=1).first() or SiteSettings()
        form = SiteSettingsForm(request.POST, instance=instance)
        if form.is_valid():
            try:
                form.save()
            except StaleSiteSettings:
                form.add_error(None, "These settings changed while you were editing. Your entries are shown below. Open the current settings in another tab and compare them before saving again.")
                return render(request, self.template_name, {"settings_form": form}, status=409)
            messages.success(request, "Site settings saved.")
            return redirect("dashboard:site_settings")
        return render(request, self.template_name, {"settings_form": form}, status=200)
