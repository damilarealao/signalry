# queues/admin.py
from django.contrib import admin
from .models import QueueJob, Queue

@admin.register(QueueJob)
class QueueJobAdmin(admin.ModelAdmin):
    list_display = ['job_type', 'user', 'status', 'priority', 'created_at']
    list_filter = ['status', 'job_type', 'created_at']
    search_fields = ['user__email', 'job_type']

@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    list_display = ['name', 'timeout', 'max_retries', 'priority']
    search_fields = ['name']