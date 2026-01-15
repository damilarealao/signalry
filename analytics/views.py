# analytics/views.py

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CampaignAnalytics, UserAnalytics
from .serializers import CampaignAnalyticsSerializer, UserAnalyticsSerializer
from campaigns.models import Campaign
from django.contrib.auth import get_user_model

User = get_user_model()


class CampaignAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, campaign_id):
        campaign = get_object_or_404(
            Campaign,
            id=campaign_id,
            user=request.user
        )

        analytics, _ = CampaignAnalytics.objects.get_or_create(
            campaign=campaign
        )
        analytics.compute()

        serializer = CampaignAnalyticsSerializer(analytics)
        return Response(serializer.data)


class UserAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        if user_id is not None:
            user = get_object_or_404(User, id=user_id)
        else:
            user = request.user

        analytics, _ = UserAnalytics.objects.get_or_create(
            user=user
        )
        analytics.compute()

        serializer = UserAnalyticsSerializer(analytics)
        return Response(serializer.data)
