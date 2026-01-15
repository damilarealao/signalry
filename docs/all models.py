# analytics/models.py

from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from message_system.models import Message, MessageOpen
from campaigns.models import Campaign
from smtp.models import SMTPAccount
from deliverability.models import DomainCheck, EmailCheck
from users.models import User


# -------------------- Campaign Analytics --------------------
class CampaignAnalytics(models.Model):
    campaign = models.OneToOneField(
        Campaign, on_delete=models.CASCADE, related_name="analytics"
    )
    total_messages = models.PositiveIntegerField(default=0)
    sent_messages = models.PositiveIntegerField(default=0)
    failed_messages = models.PositiveIntegerField(default=0)
    opened_messages = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Campaign Analytics"  # ADD THIS LINE

    def compute(self):
        msgs = self.campaign.messages.all()
        self.total_messages = msgs.count()
        self.sent_messages = msgs.filter(status="sent").count()
        self.failed_messages = msgs.filter(status="failed").count()
        self.opened_messages = MessageOpen.objects.filter(message__in=msgs).count()
        self.updated_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Analytics for {self.campaign.name}"


# -------------------- User Analytics --------------------
class UserAnalytics(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="analytics")
    total_campaigns = models.PositiveIntegerField(default=0)
    active_campaigns = models.PositiveIntegerField(default=0)
    total_messages = models.PositiveIntegerField(default=0)
    average_message_opens = models.FloatField(default=0.0)
    smtp_active_accounts = models.PositiveIntegerField(default=0)
    smtp_failed_accounts = models.PositiveIntegerField(default=0)
    domains_checked = models.PositiveIntegerField(default=0)
    emails_checked = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "User Analytics"  # ADD THIS LINE

    def compute(self):
        campaigns = getattr(self.user, "campaigns", User.objects.none()).all()
        messages = Message.objects.filter(campaign__in=campaigns)
        opens = MessageOpen.objects.filter(message__in=messages)
        smtp_accounts = SMTPAccount.objects.filter(user=self.user)

        total_messages_count = messages.count()

        self.total_campaigns = campaigns.count()
        self.active_campaigns = campaigns.filter(status="active").count()
        self.total_messages = total_messages_count
        self.average_message_opens = opens.count() / total_messages_count if total_messages_count else 0
        self.smtp_active_accounts = smtp_accounts.filter(status="active").count()
        self.smtp_failed_accounts = smtp_accounts.filter(status="failed").count()
        self.domains_checked = DomainCheck.objects.filter(user=self.user).count()
        self.emails_checked = EmailCheck.objects.filter(user=self.user).count()
        self.updated_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Analytics for {self.user.email}"


# -------------------- Signals --------------------
# Campaign analytics updates
@receiver([post_save, post_delete], sender=Message)
@receiver([post_save, post_delete], sender=MessageOpen)
def update_campaign_analytics(sender, instance, **kwargs):
    campaign = getattr(instance, "campaign", None) or getattr(getattr(instance, "message", None), "campaign", None)
    if not campaign:
        return

    analytics, _ = CampaignAnalytics.objects.get_or_create(campaign=campaign)
    analytics.compute()


# User analytics updates
@receiver([post_save, post_delete], sender=Campaign)
@receiver([post_save, post_delete], sender=SMTPAccount)
@receiver([post_save, post_delete], sender=DomainCheck)
@receiver([post_save, post_delete], sender=EmailCheck)
@receiver([post_save, post_delete], sender=Message)
@receiver([post_save, post_delete], sender=MessageOpen)
def update_user_analytics(sender, instance, **kwargs):
    user = getattr(instance, "user", None)
    if not user:
        campaign = getattr(instance, "campaign", None) or getattr(getattr(instance, "message", None), "campaign", None)
        user = getattr(campaign, "user", None) if campaign else None

    if not user:
        return

    analytics, _ = UserAnalytics.objects.get_or_create(user=user)
    analytics.compute()

# Note: These signals will trigger compute() on every save/delete,
# which may impact performance if you have large numbers of messages or campaigns.
# Consider adding @transaction.atomic or batching updates for high-scale systems.

# campaigns/models.py

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from plans.models import Plan

STATUS_CHOICES = [
    ("draft", "Draft"),
    ("paused", "Paused"),
    ("active", "Active"),
    ("completed", "Completed"),
    ("failed", "Failed"),
]


class CampaignManager(models.Manager):
    def create_campaign(self, user, name, scheduled_at=None, status="draft"):
        """
        Create a campaign while enforcing the user's plan limits.
        Draft status by default. Raises ValidationError if limit exceeded.
        """
        # Use the user's current plan property; fallback to free if none
        user_plan = getattr(user, "current_plan", None)
        plan_type = getattr(user_plan, "plan_type", "free") if user_plan else "free"
        plan_limit = Plan.objects.get_limits(plan_type)["active_campaigns"]

        if plan_limit is not None:
            # Count draft + active campaigns toward the plan limit
            active_count = user.campaigns.filter(status__in=["draft", "active"]).count()
            if active_count >= plan_limit:
                raise ValidationError(
                    "User has reached the maximum number of campaigns for their plan."
                )

        campaign = self.model(
            user=user,
            name=name,
            scheduled_at=scheduled_at or timezone.now(),
            status=status
        )
        campaign.full_clean()
        campaign.save(using=self._db)
        return campaign


class Campaign(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="campaigns"
    )
    name = models.CharField(max_length=255)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CampaignManager()

    def preflight_validate(self):
        """
        Validate campaign before sending.
        Only drafts or paused campaigns can pass preflight.
        """
        if not self.name.strip():
            raise ValidationError("Campaign name cannot be empty.")
        if self.status not in ["draft", "paused"]:
            raise ValidationError(
                "Campaign status must be 'draft' or 'paused' for preflight validation."
            )
        return True

    def __str__(self):
        return f"{self.name} ({self.status})"


# deliverability/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

CHECK_STATUS_CHOICES = [
    ("pass", "Pass"),
    ("fail", "Fail"),
    ("neutral", "Neutral"),
    ("unknown", "Unknown"),
]

RISK_LEVEL_CHOICES = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
]


class DomainCheck(models.Model):
    """
    Store results of a single domain deliverability check.
    Includes SPF, DKIM, DMARC results and a risk assessment.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="domain_checks",
        null=True,
        blank=True,
    )
    domain = models.CharField(max_length=255)
    spf = models.CharField(max_length=10, choices=CHECK_STATUS_CHOICES, default="unknown")
    dkim = models.CharField(max_length=10, choices=CHECK_STATUS_CHOICES, default="unknown")
    dmarc = models.CharField(max_length=10, choices=CHECK_STATUS_CHOICES, default="unknown")
    risk_score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True)
    last_checked = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("domain", "user")
        indexes = [
            models.Index(fields=["domain"]),
            models.Index(fields=["last_checked"]),
        ]

    def __str__(self):
        return f"{self.domain} ({self.risk_level or 'unknown'})"

    def update_risk_level(self):
        """
        Compute risk level based on SPF/DKIM/DMARC results.
        """
        score = 0
        for field in [self.spf, self.dkim, self.dmarc]:
            if field == "pass":
                score += 0
            elif field == "neutral":
                score += 1
            else:  # fail or unknown
                score += 2

        self.risk_score = score
        if score <= 2:
            self.risk_level = "low"
        elif score <= 4:
            self.risk_level = "medium"
        else:
            self.risk_level = "high"
        self.save(update_fields=["risk_score", "risk_level", "updated_at"])


class EmailCheck(models.Model):
    """
    Store results of single email SMTP validation.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_checks")
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=[("valid","Valid"),("invalid","Invalid"),("unknown","Unknown")], default="unknown")
    domain_type = models.CharField(max_length=20, choices=[("free","Free"),("premium","Premium"),("disposable","Disposable")], default="free")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("email", "user")
        indexes = [
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.status})"


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


# plans/models.py

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import User

# -------------------- Plan Definitions --------------------
PLAN_CHOICES = [
    ("free", "Free"),
    ("premium", "Premium"),
]

DEFAULT_LIMITS = {
    "free": {
        "smtp_accounts": 1,
        "rotation_groups": 1,  # Fixed: was 0, now at least 1
        "daily_send_limit": 500,
        "active_campaigns": 3,
    },
    "premium": {
        "smtp_accounts": None,  # unlimited
        "rotation_groups": None,
        "daily_send_limit": None,
        "active_campaigns": None,
    }
}

# -------------------- Manager --------------------
class PlanManager(models.Manager):
    def create_plan_for_user(self, user, plan_type="free"):
        if plan_type not in dict(PLAN_CHOICES):
            raise ValidationError(f"Invalid plan type: {plan_type}")
        plan = self.model(user=user, plan_type=plan_type)
        plan.full_clean()
        plan.save(using=self._db)
        return plan

    def get_limits(self, plan_type):
        """Return limits for a given plan_type."""
        return DEFAULT_LIMITS.get(plan_type, DEFAULT_LIMITS["free"])

    # ---------------- Helpers for enforcement ----------------
    def _get_user_plan(self, user):
        """Return the latest plan assigned to user, or None."""
        return user.plans.last()

    def can_create_smtp(self, user):
        """Check if user can create a new SMTP account based on plan."""
        plan = self._get_user_plan(user)
        if not plan:
            return False  # no plan assigned
        limit = self.get_limits(plan.plan_type)["smtp_accounts"]
        if limit is None:  # unlimited
            return True
        return user.smtp_accounts.count() < limit

    def can_create_rotation_group(self, user):
        """Check if user can create a new rotation group."""
        plan = self._get_user_plan(user)
        if not plan:
            return False
        limit = self.get_limits(plan.plan_type)["rotation_groups"]
        if limit is None:
            return True
        rotation_groups = (
            user.smtp_accounts
            .exclude(rotation_group__isnull=True)
            .values_list("rotation_group", flat=True)
            .distinct()
        )
        return rotation_groups.count() < limit

    def can_create_campaign(self, user):
        """Check if user can create a new active campaign based on plan."""
        plan = self._get_user_plan(user)
        if not plan:
            return False
        limit = self.get_limits(plan.plan_type)["active_campaigns"]
        if limit is None:
            return True
        # Count only campaigns that are not completed or failed
        active_count = user.campaigns.filter(status__in=["draft", "active", "paused"]).count()
        return active_count < limit

# -------------------- Plan Model --------------------
class Plan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="plans")
    plan_type = models.CharField(max_length=10, choices=PLAN_CHOICES, default="free")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PlanManager()

    def get_limits(self):
        """Return the current plan's limits."""
        return self.__class__.objects.get_limits(self.plan_type)

    def __str__(self):
        return f"{self.user.email} -> {self.plan_type}"


# queues/models.py
from django.db import models
from django.utils import timezone


class QueueJob(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    job_type = models.CharField(max_length=50)
    payload = models.JSONField()
    priority = models.IntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    scheduled_for = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job_type} ({self.status}) - {self.user.email}"


class Queue(models.Model):
    name = models.CharField(max_length=50)
    timeout = models.PositiveIntegerField(default=60)
    max_retries = models.PositiveIntegerField(default=3)
    backoff = models.PositiveIntegerField(default=5)
    priority = models.PositiveSmallIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# smtp/models.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.encryption import encrypt, decrypt
from users.models import User
import random
import logging

logger = logging.getLogger(__name__)

STATUS_CHOICES = [
    ("active", "Active"),
    ("disabled", "Disabled"),
    ("failed", "Failed"),
]

class SMTPAccountManager(models.Manager):

    def validate_smtp(self, host, port, smtp_user, smtp_password):
        """Test SMTP connection and authentication before saving."""
        try:
            server = smtplib.SMTP(host, port, timeout=5)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.quit()
        except Exception as e:
            raise ValidationError(f"SMTP test failed: {e}")

    def create_smtp(self, user, host, port, smtp_user, smtp_password, rotation_group=None):
        """Create and validate an SMTP account."""
        # Test SMTP credentials first
        self.validate_smtp(host, port, smtp_user, smtp_password)

        account = self.model(
            user=user,
            smtp_host=host,
            smtp_port=port,
            smtp_user=smtp_user,
            smtp_password_encrypted=encrypt(smtp_password),
            rotation_group=rotation_group,
            status="active",
            last_health_check=timezone.now(),
            failure_count=0
        )
        account.full_clean()
        account.save(using=self._db)
        return account

    def disable_if_failed(self, smtp_account, failure_threshold=3):
        """Automatically disable account if failures exceed threshold."""
        if smtp_account.failure_count >= failure_threshold:
            smtp_account.status = "disabled"
            smtp_account.save(update_fields=["status"])
            return True
        return False

    def get_smtp_for_sending(self, user, rotation_group=None, specific_account=None):
        """
        Return an SMTP account for sending.
        - If `specific_account` is provided, use it.
        - Otherwise, pick a random active account from `rotation_group`.
        """
        if specific_account:
            if specific_account.status != "active":
                raise ValidationError("Selected SMTP account is not active")
            return specific_account

        qs = self.filter(user=user, status="active")
        if rotation_group:
            qs = qs.filter(rotation_group=rotation_group)

        accounts = list(qs)
        if not accounts:
            raise ValidationError("No active SMTP accounts available for sending")
        return random.choice(accounts)

    def send_email(self, user, to_email, subject, body, html=False, rotation_group=None, specific_account=None):
        """
        Send an email using a chosen SMTP.
        - `html=True` sends HTML content, otherwise plain text.
        """
        smtp_account = self.get_smtp_for_sending(user, rotation_group, specific_account)
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_account.smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject

            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_account.smtp_host, smtp_account.smtp_port, timeout=10)
            server.starttls()
            
            # Get password with error handling
            password = smtp_account.get_password()
            if not password:
                raise ValidationError(f"SMTP account {smtp_account.smtp_user} has invalid credentials")
                
            server.login(smtp_account.smtp_user, password)
            server.sendmail(smtp_account.smtp_user, to_email, msg.as_string())
            server.quit()

            # Reset failure count on success
            smtp_account.reset_failures()
            return True

        except Exception as e:
            logger.error(f"Failed to send email using SMTP account {smtp_account.id}: {e}")
            smtp_account.mark_failure()
            raise

class SMTPAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="smtp_accounts")
    smtp_host = models.CharField(max_length=255)
    smtp_port = models.PositiveIntegerField()
    smtp_user = models.CharField(max_length=255)
    smtp_password_encrypted = models.TextField()
    rotation_group = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    last_health_check = models.DateTimeField(blank=True, null=True)
    failure_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SMTPAccountManager()

    def get_password(self):
        """Get decrypted password with error handling."""
        try:
            password = decrypt(self.smtp_password_encrypted)
            if not password:
                # Password decryption returned empty string
                logger.warning(f"Empty password after decryption for SMTP account {self.id}")
                self.status = "failed"
                self.save(update_fields=["status"])
            return password
        except Exception as e:
            # Log the error and mark account as failed
            logger.error(f"Failed to decrypt password for SMTP account {self.id}: {e}")
            self.status = "failed"
            self.save(update_fields=["status"])
            return ""

    def mark_failure(self):
        """Increment failure counter and auto-disable if needed."""
        self.failure_count += 1
        self.last_health_check = timezone.now()
        self.save(update_fields=["failure_count", "last_health_check"])
        self.__class__.objects.disable_if_failed(self)

    def reset_failures(self):
        """Reset failure count and restore active status."""
        self.failure_count = 0
        self.status = "active"
        self.last_health_check = timezone.now()
        self.save(update_fields=["failure_count", "status", "last_health_check"])
    
    def test_connection(self):
        """Test the SMTP connection with current credentials."""
        try:
            password = self.get_password()
            if not password:
                return False, "Invalid credentials (decryption failed)"
            
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
            server.starttls()
            server.login(self.smtp_user, password)
            server.quit()
            self.reset_failures()
            return True, "Connection successful"
        except smtplib.SMTPAuthenticationError:
            self.mark_failure()
            return False, "Authentication failed"
        except smtplib.SMTPException as e:
            self.mark_failure()
            return False, f"SMTP error: {str(e)}"
        except Exception as e:
            self.mark_failure()
            return False, f"Connection error: {str(e)}"

    def __str__(self):
        return f"{self.smtp_user}@{self.smtp_host} ({self.status})"
    
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


# users/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    # Avoid clashes with default auth.User
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups"
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions"
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # No additional fields required for superuser

    def __str__(self):
        return self.email
    
    def get_display_name(self):
        """
        Get display name for greetings - use full_name if available, 
        otherwise email prefix.
        
        Returns:
            str: Display name for the user
        """
        if self.full_name and self.full_name.strip():
            return self.full_name.strip()
        
        # Fallback to email username (part before @)
        if '@' in self.email:
            return self.email.split('@')[0]
        
        return self.email

    # ---------------- Plan Helpers ----------------
    @property
    def current_plan(self):
        """
        Returns the latest Plan instance assigned to the user.
        Returns None if no plan exists.
        """
        return self.plans.last()  # 'plans' is the related_name in Plan model

    @property
    def plan_type(self):
        """
        Returns the plan_type of the user's latest plan.
        Defaults to 'free' if no plan is assigned.
        """
        plan = self.current_plan
        return plan.plan_type if plan else "free"