# tracking/views.py
from rest_framework import status, generics
from rest_framework.response import Response
from .models import Click
from .serializers import ClickSerializer
from message_system.models import Message
import hashlib

class RecordClickView(generics.CreateAPIView):
    """
    Endpoint to record clicks from messages.
    Requires beacon_uuid, url, optional ip and user_agent.
    """
    serializer_class = ClickSerializer

    def post(self, request, *args, **kwargs):
        beacon_uuid = request.data.get("beacon_uuid")
        url = request.data.get("url")
        raw_ip = request.data.get("ip")
        user_agent = request.data.get("user_agent_family", "")

        try:
            message = Message.objects.get(uuid=beacon_uuid)
        except Message.DoesNotExist:
            return Response({"detail": "Message not found"}, status=status.HTTP_404_NOT_FOUND)

        ip_hash = hashlib.sha256(raw_ip.encode("utf-8")).hexdigest() if raw_ip else None
        click = Click.objects.create(
            message=message,
            beacon_uuid=beacon_uuid,
            url=url,
            ip_hash=ip_hash,
            user_agent_family=user_agent
        )
        serializer = self.get_serializer(click)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
