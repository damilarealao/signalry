#message_system/models.py

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from campaigns.models import Campaign
from smtp.models import SMTPAccount
import uuid
import hashlib


STATUS_CHOICES = [
    ("draft", "Draft"),
    ("queued", "Queued"),
    ("sent", "Sent"),
    ("failed", "Failed"),
    ("retried", "Retried"),
]


# -------------------- Message Manager --------------------
class MessageManager(models.Manager):
    def create_message(self, campaign, subject, body_plain="", body_html="", sender_smtp=None):
        if not campaign:
            raise ValidationError("Campaign is required to create a message.")

        message = self.model(
            campaign=campaign,
            uuid=str(uuid.uuid4()),
            subject=subject,
            body_plain=body_plain,
            body_html=body_html,
            sender_smtp=sender_smtp,
            status="draft",
            created_at=timezone.now(),
        )
        message.full_clean()
        message.save(using=self._db)
        return message


# -------------------- Message Model --------------------
class Message(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    uuid = models.CharField(max_length=36, unique=True)
    subject = models.CharField(max_length=255)
    body_plain = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    sender_smtp = models.ForeignKey(
        SMTPAccount,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    retries = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MessageManager()

    # -------------------- State transitions --------------------
    def mark_sent(self):
        self.status = "sent"
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "updated_at"])

    def mark_failed(self):
        self.status = "failed"
        self.save(update_fields=["status", "updated_at"])

    def retry(self):
        self.status = "retried"
        self.retries += 1
        self.save(update_fields=["status", "retries", "updated_at"])

    def __str__(self):
        return f"{self.subject} ({self.status})"


# -------------------- MessageOpen Manager --------------------
class MessageOpenManager(models.Manager):
    def record_open(self, message, raw_ip=None, user_agent_family="", beacon_uuid=None):
        """
        Canonical entry point for recording opens.
        All privacy rules enforced here.
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
            beacon_uuid=beacon_uuid,
            ip_hash=ip_hash,
            user_agent_family=user_agent_family,
            opened_at=timezone.now(),
        )


# -------------------- MessageOpen Model --------------------
class MessageOpen(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="opens"
    )
    beacon_uuid = models.CharField(max_length=36)
    ip_hash = models.CharField(max_length=64, blank=True, null=True)
    user_agent_family = models.CharField(max_length=50, blank=True)
    opened_at = models.DateTimeField(default=timezone.now)

    objects = MessageOpenManager()

    class Meta:
        indexes = [
            models.Index(fields=["beacon_uuid"]),
            models.Index(fields=["opened_at"]),
        ]

    def save(self, *args, **kwargs):
        # Defensive layer: ensure UA is coarse even if misused
        if self.user_agent_family:
            self.user_agent_family = self.user_agent_family.split("/")[0][:50]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Open for {self.message.uuid} at {self.opened_at}"
