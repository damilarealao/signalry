# plans/tests.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from users.models import User
from smtp.models import SMTPAccount
from campaigns.models import Campaign
from .models import Plan, DEFAULT_LIMITS
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

class PlanEnforcementTests(TestCase):
    def setUp(self):
        self.user_free = User.objects.create_user(email="free@test.com", password="pass123")
        self.user_premium = User.objects.create_user(email="premium@test.com", password="pass123")
        Plan.objects.create_plan_for_user(self.user_free, "free")
        Plan.objects.create_plan_for_user(self.user_premium, "premium")

    @patch("smtp.models.smtplib.SMTP")
    def test_can_create_smtp_limit(self, mock_smtp):
        # Mock SMTP to always succeed
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        limit = DEFAULT_LIMITS["free"]["smtp_accounts"]

        # initially should allow
        self.assertTrue(Plan.objects.can_create_smtp(self.user_free))

        # fill up to limit
        for i in range(limit):
            SMTPAccount.objects.create_smtp(
                user=self.user_free,
                host=f"smtp{i}.test.com",
                port=587,
                smtp_user=f"user{i}@test.com",
                smtp_password="pass123"
            )

        # should now block creation
        self.assertFalse(Plan.objects.can_create_smtp(self.user_free))

    def test_can_create_rotation_group_limit(self):
        # Free plan has 0 rotation groups
        self.assertFalse(Plan.objects.can_create_rotation_group(self.user_free))

        # Premium plan is unlimited
        self.assertTrue(Plan.objects.can_create_rotation_group(self.user_premium))

    def test_can_create_campaign_limit(self):
        limit = DEFAULT_LIMITS["free"]["active_campaigns"]

        # initially should allow
        self.assertTrue(Plan.objects.can_create_campaign(self.user_free))

        # fill up to limit with dummy campaigns
        for i in range(limit):
            Campaign.objects.create(
                user=self.user_free,
                name=f"Campaign {i}",
                status="active",
                scheduled_at=timezone.now() + timedelta(days=i)
            )

        # should now block creation
        self.assertFalse(Plan.objects.can_create_campaign(self.user_free))
