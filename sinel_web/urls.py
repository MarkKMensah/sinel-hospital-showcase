"""sinel_web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("website.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("blog/", include("blog.urls")),
    path("api/v1/", include("rest_api_v1.urls")),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("communications/", include("communications.urls")),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Customize django admin page.
admin.site.site_header = "SINEL HOSPITAL ADMINISTRATION" # default: "Django Administration"
admin.site.index_title = "Site Adminsitration"                    # default: "Site administration"
admin.site.site_title =  'Sinel site admin'                # default: "Django site admin"
