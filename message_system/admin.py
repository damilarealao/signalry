# message_system/admin.py
from django.contrib import admin
from .models import Message, MessageOpen

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['subject', 'campaign', 'status', 'sent_at', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['subject', 'campaign__name']

@admin.register(MessageOpen)
class MessageOpenAdmin(admin.ModelAdmin):
    list_display = ['message', 'beacon_uuid', 'opened_at']
    list_filter = ['opened_at']
    search_fields = ['message__subject', 'beacon_uuid']