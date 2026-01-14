# deliverability/admin.py
from django.contrib import admin
from .models import DomainCheck, EmailCheck

@admin.register(DomainCheck)
class DomainCheckAdmin(admin.ModelAdmin):
    list_display = ['domain', 'user', 'risk_level', 'last_checked']
    list_filter = ['risk_level', 'spf', 'dkim', 'dmarc']
    search_fields = ['domain', 'user__email']

@admin.register(EmailCheck)
class EmailCheckAdmin(admin.ModelAdmin):
    list_display = ['email', 'user', 'status', 'domain_type', 'created_at']
    list_filter = ['status', 'domain_type']
    search_fields = ['email', 'user__email']