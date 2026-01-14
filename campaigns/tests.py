# campaigns/tests.py
from django.test import TestCase
from users.models import User
from plans.models import Plan, DEFAULT_LIMITS
from .models import Campaign
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

class CampaignTests(TestCase):
    def setUp(self):
        """Set up free and premium users with their plans."""
        self.user_free = User.objects.create_user(email="free@test.com", password="pass123")
        self.user_premium = User.objects.create_user(email="premium@test.com", password="pass123")
        Plan.objects.create_plan_for_user(self.user_free, "free")
        Plan.objects.create_plan_for_user(self.user_premium, "premium")

    def test_campaign_creation_up_to_limit(self):
        """
        Ensure creating campaigns up to the user's plan limit works, then fails when exceeded.
        Free users can only have `DEFAULT_LIMITS["free"]["active_campaigns"]` draft/active campaigns.
        """
        limit = DEFAULT_LIMITS["free"]["active_campaigns"]

        # Create campaigns up to the limit
        for i in range(limit):
            campaign = Campaign.objects.create_campaign(
                user=self.user_free,
                name=f"Campaign {i}",
                scheduled_at=timezone.now() + timedelta(days=i)
            )
            self.assertEqual(campaign.status, "draft")

        # Attempting one more should raise ValidationError
        with self.assertRaises(ValidationError):
            Campaign.objects.create_campaign(
                user=self.user_free,
                name="Overflow Campaign",
                scheduled_at=timezone.now()
            )

    def test_campaign_creation_unlimited_for_premium(self):
        """
        Ensure premium users can create campaigns beyond the free plan limits.
        """
        limit = 10  # arbitrary number for testing
        for i in range(limit):
            campaign = Campaign.objects.create_campaign(
                user=self.user_premium,
                name=f"Premium Campaign {i}",
                scheduled_at=timezone.now() + timedelta(days=i)
            )
            self.assertEqual(campaign.status, "draft")

        # Confirm all campaigns were created
        self.assertEqual(self.user_premium.campaigns.count(), limit)

    def test_campaign_preflight_validation(self):
        """
        Check that preflight validation enforces rules:
        - Name cannot be empty
        - Status must be draft or paused
        """
        campaign = Campaign.objects.create_campaign(user=self.user_free, name="Test Campaign")
        
        # Preflight passes for valid draft campaign
        self.assertTrue(campaign.preflight_validate())

        # Invalid name should raise ValidationError
        campaign.name = ""
        with self.assertRaises(ValidationError):
            campaign.preflight_validate()

        # Invalid status for preflight
        campaign.name = "Fixed Name"
        campaign.status = "active"  # preflight only works for draft/paused
        with self.assertRaises(ValidationError):
            campaign.preflight_validate()
