from django.urls import path
from . import views

urlpatterns = [
    path("test-dashboard/", views.test_dashboard, name="test-dashboard"),
]
