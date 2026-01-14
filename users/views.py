# users/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required  # optional

# Create your views here.

# Remove @login_required if you want the dashboard public
@login_required
def test_dashboard(request):
    """
    A simple test dashboard view for Signalry frontend testing.
    This uses dummy data to simulate user, campaigns, SMTP accounts, and analytics.
    """
    # Example context with dummy data
    context = {
        "user": {
            "email": "user@test.com",
            "full_name": "John Doe",
            "plan_type": "Free",
        },
        "analytics": {
            "total_campaigns": 5,
            "active_campaigns": 2,
            "total_messages": 120,
            "average_message_opens": 45,
            "smtp_active_accounts": 1,
            "smtp_failed_accounts": 0,
            "domains_checked": 3,
            "emails_checked": 50,
        },
        "smtp_accounts": [
            {"host": "smtp.mail.com", "status": "active", "failure_count": 0},
            {"host": "smtp2.mail.com", "status": "disabled", "failure_count": 2},
        ],
        "campaigns": [
            {"name": "Campaign 1", "status": "sent", "scheduled_at": "2026-01-13"},
            {"name": "Campaign 2", "status": "queued", "scheduled_at": "2026-01-14"},
            {"name": "Campaign 3", "status": "draft", "scheduled_at": "2026-01-15"},
        ],
    }
    return render(request, "core/test_dashboard.html", context)
