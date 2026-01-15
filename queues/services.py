# queues/services.py
from django.utils import timezone

from queues.selectors import get_messages_ready_for_sending
from queues.executor import execute_message_send


def run_message_queue(batch_size=20):
    messages = get_messages_ready_for_sending(limit=batch_size)

    results = {
        "processed": 0,
        "sent": 0,
        "failed": 0,
    }

    for message in messages:
        results["processed"] += 1

        success = execute_message_send(message)

        if success:
            message.status = "sent"
            message.sent_at = timezone.now()
            message.save(update_fields=["status", "sent_at", "updated_at"])
            results["sent"] += 1
        else:
            message.retries += 1  # <-- aligned with Message model

            if message.retries >= getattr(message, "max_retries", 3):
                message.status = "failed"
                results["failed"] += 1
            else:
                message.status = "retried"

            message.save(update_fields=["status", "retries", "updated_at"])

    return results
