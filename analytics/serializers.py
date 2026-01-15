# analytics/serializers.py

from rest_framework import serializers
from .models import CampaignAnalytics, UserAnalytics

class CampaignAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignAnalytics
        fields = "__all__"

class UserAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAnalytics
        fields = "__all__"
