# tracking/urls.py
from django.urls import path
from .views import RecordClickView

urlpatterns = [
    path("clicks/", RecordClickView.as_view(), name="record_click"),
]
