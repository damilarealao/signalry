# tracking/serializers.py
from rest_framework import serializers
from .models import Click

class ClickSerializer(serializers.ModelSerializer):
    class Meta:
        model = Click
        fields = ["beacon_uuid", "url", "ip_hash", "user_agent_family", "clicked_at"]
        read_only_fields = ["clicked_at"]
