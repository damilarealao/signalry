# deliverability/urls.py
from django.urls import path
from .views import DomainCheckView, DomainCheckListView, EmailCheckView, EmailBulkCheckView

app_name = "deliverability"

urlpatterns = [
    # -------------------
    # Domain Deliverability
    # -------------------
    path("domains/check/", DomainCheckView.as_view(), name="domain-check"),
    path("domains/", DomainCheckListView.as_view(), name="domain-check-list"),

    # -------------------
    # Email Deliverability (SMTP)
    # -------------------
    path("emails/check/", EmailCheckView.as_view(), name="email-check"),
    path("emails/bulk-check/", EmailBulkCheckView.as_view(), name="email-bulk-check"),
]
