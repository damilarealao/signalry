# analytics/admin.py
from django.contrib import admin
from .models import CampaignAnalytics, UserAnalytics

@admin.register(CampaignAnalytics)
class CampaignAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'total_messages', 'sent_messages', 'opened_messages']
    search_fields = ['campaign__name']

@admin.register(UserAnalytics)
class UserAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_campaigns', 'active_campaigns', 'total_messages']
    search_fields = ['user__email']