# analytics/management/commands/compute_analytics.py

from django.core.management.base import BaseCommand
from analytics.models import CampaignAnalytics, UserAnalytics
from campaigns.models import Campaign
from users.models import User

class Command(BaseCommand):
    help = "Compute all analytics for campaigns and users"

    def handle(self, *args, **options):
        for campaign in Campaign.objects.all():
            analytics, _ = CampaignAnalytics.objects.get_or_create(campaign=campaign)
            analytics.compute()
            self.stdout.write(f"Computed analytics for campaign {campaign.id}")

        for user in User.objects.all():
            analytics, _ = UserAnalytics.objects.get_or_create(user=user)
            analytics.compute()
            self.stdout.write(f"Computed analytics for user {user.id}")
