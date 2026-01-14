# campaigns/admin.py
from django.contrib import admin
from .models import Campaign

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'status', 'scheduled_at', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'user__email']