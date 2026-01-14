# smtp/admin.py
from django.contrib import admin
from .models import SMTPAccount

@admin.register(SMTPAccount)
class SMTPAccountAdmin(admin.ModelAdmin):
    list_display = ['smtp_user', 'smtp_host', 'user', 'status', 'last_health_check']
    list_filter = ['status', 'rotation_group']
    search_fields = ['smtp_user', 'user__email', 'smtp_host']