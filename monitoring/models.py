# monitoring/models.py

from django.db import models
from django.utils import timezone
from users.models import User
from campaigns.models import Campaign
from smtp.models import SMTPAccount

# -------------------- Choices --------------------
LOG_LEVEL_CHOICES = [
    ("info", "Info"),
    ("warning", "Warning"),
    ("error", "Error"),
]

ALERT_TYPE_CHOICES = [
    ("failed_campaign", "Failed Campaign"),
    ("smtp_unreachable", "SMTP Unreachable"),
    ("threshold_exceeded", "Threshold Exceeded"),
]


# -------------------- Managers --------------------
class SystemLogManager(models.Manager):
    def record(self, user, message, level="info", campaign=None, smtp_account=None):
        return self.create(
            user=user,
            campaign=campaign,
            smtp_account=smtp_account,
            level=level,
            message=message,
            created_at=timezone.now(),
        )


class MetricManager(models.Manager):
    def record(self, user, name, value, campaign=None, smtp_account=None):
        return self.create(
            user=user,
            campaign=campaign,
            smtp_account=smtp_account,
            name=name,
            value=value,
            recorded_at=timezone.now(),
        )


class AlertManager(models.Manager):
    def trigger(self, user, alert_type, message, campaign=None, smtp_account=None):
        return self.create(
            user=user,
            campaign=campaign,
            smtp_account=smtp_account,
            alert_type=alert_type,
            message=message,
            is_resolved=False,
            created_at=timezone.now(),
        )


# -------------------- Models --------------------
class SystemLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="logs")
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    smtp_account = models.ForeignKey(SMTPAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    objects = SystemLogManager()

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["campaign"]),
            models.Index(fields=["smtp_account"]),
            models.Index(fields=["level"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.level.upper()}] {self.user.email}: {self.message[:50]}"


class Metric(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="metrics")
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="metrics")
    smtp_account = models.ForeignKey(SMTPAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name="metrics")
    name = models.CharField(max_length=100)
    value = models.FloatField()
    recorded_at = models.DateTimeField(default=timezone.now)

    objects = MetricManager()

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["campaign"]),
            models.Index(fields=["smtp_account"]),
            models.Index(fields=["name"]),
            models.Index(fields=["recorded_at"]),
        ]
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.name}={self.value} for {self.user.email} at {self.recorded_at}"


class Alert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="alerts")
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts")
    smtp_account = models.ForeignKey(SMTPAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts")
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    objects = AlertManager()

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["campaign"]),
            models.Index(fields=["smtp_account"]),
            models.Index(fields=["alert_type"]),
            models.Index(fields=["is_resolved"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def mark_resolved(self):
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save(update_fields=["is_resolved", "resolved_at"])

    def __str__(self):
        status = "RESOLVED" if self.is_resolved else "ACTIVE"
        return f"[{status}] {self.alert_type} for {self.user.email}: {self.message[:50]}"
