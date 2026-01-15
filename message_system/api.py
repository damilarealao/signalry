# message_system/api.py
from rest_framework import viewsets, permissions
from .models import MessageOpen
from .serializers import MessageOpenSerializer

class MessageOpenViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to message opens.
    User can ONLY see opens for messages in their own campaigns.
    """
    serializer_class = MessageOpenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        qs = MessageOpen.objects.filter(
            message__campaign__user=user
        ).select_related("message")

        # Optional: filter by message UUID via query param
        beacon_uuid = self.request.query_params.get("beacon_uuid")
        if beacon_uuid:
            qs = qs.filter(beacon_uuid=beacon_uuid)

        return qs.order_by("-opened_at")
