# queues/executor.py
from django.utils import timezone
from smtp.models import SMTPAccount
from message_system.models import Message

def execute_message_send(message: Message):
    """
    Executes a single message send.
    This is intentionally synchronous.
    """

    if message.status not in ("queued", "retried"):
        return False

    try:
        SMTPAccount.objects.send_email(
            user=message.campaign.user,
            to_email=message.campaign.target_email,
            subject=message.subject,
            body=message.body_html or message.body_plain,
            html=bool(message.body_html),
            specific_account=message.sender_smtp,
        )

        message.mark_sent()
        return True

    except Exception:
        if message.retries >= 3:
            message.mark_failed()
        else:
            message.retry()
        return False
