# tracking/models.py
from django.db import models
from django.utils import timezone
from message_system.models import Message
import hashlib


# -------------------- Click Manager --------------------
class ClickManager(models.Manager):
    def record_click(self, message, url, raw_ip=None, user_agent_family="", beacon_uuid=None):
        """
        Canonical entry point for recording clicks.
        Handles IP hashing and user agent truncation for privacy.
        """
        if beacon_uuid is None:
            beacon_uuid = message.uuid

        ip_hash = None
        if raw_ip:
            ip_hash = hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()

        if user_agent_family:
            user_agent_family = user_agent_family.split("/")[0][:50]

        return self.create(
            message=message,
            url=url,
            beacon_uuid=beacon_uuid,
            ip_hash=ip_hash,
            user_agent_family=user_agent_family,
            clicked_at=timezone.now(),
        )


# -------------------- Click Model --------------------
class Click(models.Model):
    """
    Record a user clicking a tracked link inside a message.
    Minimal privacy info is stored: hashed IP, coarse user agent.
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

    objects = ClickManager()

    class Meta:
        indexes = [
            models.Index(fields=["beacon_uuid"]),
            models.Index(fields=["clicked_at"]),
        ]

    def save(self, *args, **kwargs):
        # Defensive: truncate user agent
        if self.user_agent_family:
            self.user_agent_family = self.user_agent_family.split("/")[0][:50]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Click for {self.message.uuid} on {self.url} at {self.clicked_at}"
