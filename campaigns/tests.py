# campaigns/tests.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from users.models import User
from plans.models import Plan, DEFAULT_LIMITS
from .models import Campaign

class CampaignModelTests(TestCase):

    def setUp(self):
        # Create users
        self.user_free = User.objects.create_user(email="free@test.com", password="pass123")
        self.user_premium = User.objects.create_user(email="premium@test.com", password="pass123")

        # Assign plans
        Plan.objects.create_plan_for_user(self.user_free, "free")
        Plan.objects.create_plan_for_user(self.user_premium, "premium")

    def test_create_campaign_under_limit(self):
        """User can create campaigns within plan limit"""
        limit = DEFAULT_LIMITS["free"]["active_campaigns"]
        for i in range(limit):
            campaign = Campaign.objects.create_campaign(
                user=self.user_free,
                name=f"Campaign {i}",
                scheduled_at=timezone.now() + timedelta(days=i)
            )
            self.assertEqual(campaign.user, self.user_free)
            self.assertEqual(campaign.status, "draft")
            self.assertTrue(campaign.name.startswith("Campaign"))

    def test_create_campaign_over_limit_raises_error(self):
        """Creating campaigns beyond plan limit raises ValidationError"""
        limit = DEFAULT_LIMITS["free"]["active_campaigns"]
        # Fill up to the limit
        for i in range(limit):
            Campaign.objects.create_campaign(
                user=self.user_free,
                name=f"Campaign {i}",
                scheduled_at=timezone.now()
            )

        # Creating one more should raise error
        with self.assertRaises(ValidationError):
            Campaign.objects.create_campaign(
                user=self.user_free,
                name="Exceed Limit",
                scheduled_at=timezone.now()
            )

    def test_preflight_validate(self):
        """Preflight validation only passes for draft or paused campaigns"""
        campaign = Campaign.objects.create_campaign(
            user=self.user_free,
            name="Draft Campaign",
            status="draft"
        )
        self.assertTrue(campaign.preflight_validate())

        campaign.status = "paused"
        self.assertTrue(campaign.preflight_validate())

        campaign.status = "active"
        with self.assertRaises(ValidationError):
            campaign.preflight_validate()

    def test_empty_name_raises_validation_error(self):
        """Campaign name cannot be empty"""
        campaign = Campaign.objects.create_campaign(
            user=self.user_free,
            name="   ",  # empty/whitespace
            status="draft"
        )
        with self.assertRaises(ValidationError):
            campaign.preflight_validate()

    def test_str_method(self):
        """__str__ method returns name and status"""
        campaign = Campaign.objects.create_campaign(
            user=self.user_free,
            name="My Campaign",
            status="draft"
        )
        self.assertEqual(str(campaign), "My Campaign (draft)")
