# analytics/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from message_system.models import Message, MessageOpen
from campaigns.models import Campaign
from analytics.models import CampaignAnalytics, UserAnalytics

@receiver(post_save, sender=Message)
@receiver(post_delete, sender=Message)
def update_campaign_analytics(sender, instance, **kwargs):
    analytics, _ = CampaignAnalytics.objects.get_or_create(campaign=instance.campaign)
    analytics.compute()
    user_analytics, _ = UserAnalytics.objects.get_or_create(user=instance.campaign.user)
    user_analytics.compute()

@receiver(post_save, sender=MessageOpen)
@receiver(post_delete, sender=MessageOpen)
def update_message_open_analytics(sender, instance, **kwargs):
    instance.message.campaign.analytics.compute()
    UserAnalytics.objects.get(user=instance.message.campaign.user).compute()
