# queues/selectors.py
from message_system.models import Message

def get_messages_ready_for_sending(limit=50):
    return (
        Message.objects
        .filter(status="queued")
        .order_by("created_at")[:limit]
    )
