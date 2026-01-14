# tracking/admin.py
from django.contrib import admin
from .models import Click

@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ["message", "url", "beacon_uuid", "clicked_at"]
    search_fields = ["beacon_uuid", "url"]
