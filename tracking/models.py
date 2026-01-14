# tracking/models.py
from django.db import models
from django.utils import timezone
from message_system.models import Message
import hashlib

class Click(models.Model):
    """
    Record a user clicking a tracked link inside a message.
    We store minimal privacy info.
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="clicks"
    )
    beacon_uuid = models.CharField(max_length=36)
    url = models.URLField()
    ip_hash = models.CharField(max_length=64, blank=True, null=True)
    user_agent_family = models.CharField(max_length=50, blank=True)
    clicked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["beacon_uuid"]),
            models.Index(fields=["clicked_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.user_agent_family:
            self.user_agent_family = self.user_agent_family.split("/")[0][:50]
        super().save(*args, **kwargs)
