# message_system/views.py
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

from .models import Message, MessageOpen

# 1x1 transparent PNG
PIXEL = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4"
    b"\x89\x00\x00\x00\nIDATx\xdac\xf8"
    b"\x0f\x00\x01\x01\x01\x00\x18\xdd"
    b"\x8d\x18\x00\x00\x00\x00IEND\xaeB`\x82"
)

@csrf_exempt
@require_GET
def message_beacon(request, uuid):
    """
    Tracking pixel endpoint.
    Public, write-only, privacy-safe.
    """
    try:
        message = Message.objects.get(uuid=uuid)
    except Message.DoesNotExist:
        # Never leak existence, always return pixel
        return HttpResponse(PIXEL, content_type="image/png")

    raw_ip = request.META.get("REMOTE_ADDR")
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    # Single canonical write path
    MessageOpen.objects.record_open(
        message=message,
        raw_ip=raw_ip,
        user_agent_family=user_agent,
        beacon_uuid=str(uuid),
    )

    return HttpResponse(PIXEL, content_type="image/png")
