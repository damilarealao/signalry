# analytics/urls.py

from django.urls import path
from .views import CampaignAnalyticsView, UserAnalyticsView

urlpatterns = [
    path("campaign/<int:campaign_id>/", CampaignAnalyticsView.as_view(), name="campaign-analytics"),
    path("user/<int:user_id>/", UserAnalyticsView.as_view(), name="user-analytics"),
    path("me/", UserAnalyticsView.as_view(), name="my-analytics"),
]
