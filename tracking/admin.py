# tracking/admin.py
from django.contrib import admin
from .models import Click

@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ['message', 'url', 'beacon_uuid', 'clicked_at']
    list_filter = ['clicked_at']
    search_fields = ['message__subject', 'url', 'beacon_uuid']