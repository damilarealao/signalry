# message_system/serializers.py
from rest_framework import serializers
from .models import MessageOpen

class MessageOpenSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageOpen
        fields = [
            "beacon_uuid",
            "opened_at",
            "user_agent_family",
        ]
