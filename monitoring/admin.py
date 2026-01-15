# monitoring/admin.py
from django.contrib import admin
from .models import SystemLog, Metric, Alert

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'message', 'created_at']
    list_filter = ['level', 'created_at']
    search_fields = ['user__email', 'message']

@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'value', 'recorded_at']
    list_filter = ['name', 'recorded_at']
    search_fields = ['user__email', 'name']

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'alert_type', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'is_resolved', 'created_at']
    search_fields = ['user__email', 'message']