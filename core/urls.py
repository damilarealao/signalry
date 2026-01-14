# core/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("message_system.urls")),
    path("deliverability/", include("deliverability.urls")),
    path("api/", include("analytics.urls")),
    path("api/tracking/", include("tracking.urls")),

]
