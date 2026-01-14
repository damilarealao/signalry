# analytics/models.py

from django.db import models
from django.utils import timezone
from django.db.models import Count, Avg
from message_system.models import Message, MessageOpen
from campaigns.models import Campaign
from smtp.models import SMTPAccount
from deliverability.models import DomainCheck, EmailCheck
from users.models import User

class CampaignAnalytics(models.Model):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name="analytics")
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
        campaigns = self.user.campaigns.all()
        messages = Message.objects.filter(campaign__in=campaigns)
        opens = MessageOpen.objects.filter(message__in=messages)
        smtp_accounts = SMTPAccount.objects.filter(user=self.user)

        self.total_campaigns = campaigns.count()
        self.active_campaigns = campaigns.filter(status="active").count()
        self.total_messages = messages.count()
        self.average_message_opens = opens.count() / messages.count() if messages.count() else 0
        self.smtp_active_accounts = smtp_accounts.filter(status="active").count()
        self.smtp_failed_accounts = smtp_accounts.filter(status="failed").count()
        self.domains_checked = DomainCheck.objects.filter(user=self.user).count()
        self.emails_checked = EmailCheck.objects.filter(user=self.user).count()
        self.updated_at = timezone.now()
        self.save()
