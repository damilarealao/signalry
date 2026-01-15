# plans/admin.py
from django.contrib import admin
from .models import Plan

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan_type', 'created_at']
    list_filter = ['plan_type', 'created_at']
    search_fields = ['user__email']