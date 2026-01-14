# core/urls.py - FIXED VERSION
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    
    # Main app - handles index, auth, dashboard, profile
    path("", include("users.urls")),
    
    # API Endpoints
    path("api/messages/", include("message_system.urls")),
    path("api/analytics/", include("analytics.urls")),
    path("api/tracking/", include("tracking.urls")),
    
    # Web Interface (non-API)
    path("deliverability/", include("deliverability.urls")),
    
    path('smtp/', include('smtp.urls')),
    
    path('campaigns/', include('campaigns.urls')),
]