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
