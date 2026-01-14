# message_system/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import message_beacon
from .api import MessageOpenViewSet

router = DefaultRouter()
router.register(r"message-opens", MessageOpenViewSet, basename="message-open")

urlpatterns = [
    # Public tracking pixel (write-only)
    path("t/<uuid:uuid>.png", message_beacon, name="message-beacon"),

    # Authenticated API endpoints
    path("", include(router.urls)),
]
