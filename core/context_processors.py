# core/context_processors.py
from django.conf import settings

def site_settings(request):
    """Add site settings to template context."""
    return {
        'SITE_URL': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Signalry'),
        'EMAIL_FROM_NAME': getattr(settings, 'EMAIL_FROM_NAME', 'Signalry'),
    }