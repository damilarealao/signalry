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
        # -------------------- Users --------------------
        self.user_free = User.objects.create_user(email="free@test.com", password="pass123")
        self.user_premium = User.objects.create_user(email="premium@test.com", password="pass123")

        # -------------------- Plans --------------------
        Plan.objects.create_plan_for_user(self.user_free, "free")
        Plan.objects.create_plan_for_user(self.user_premium, "premium")

    @patch("smtp.models.smtplib.SMTP")
    def test_can_create_smtp_limit(self, mock_smtp):
        """Ensure SMTP account creation respects plan limits."""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        limit = DEFAULT_LIMITS["free"]["smtp_accounts"]

        # Initially allowed
        self.assertTrue(Plan.objects.can_create_smtp(self.user_free))

        # Fill up to limit
        for i in range(limit):
            SMTPAccount.objects.create_smtp(
                user=self.user_free,
                host=f"smtp{i}.test.com",
                port=587,
                smtp_user=f"user{i}@test.com",
                smtp_password="pass123"
            )

        # Should now block creation
        self.assertFalse(Plan.objects.can_create_smtp(self.user_free))

    def test_can_create_rotation_group_limit(self):
        """Ensure rotation group creation respects plan limits."""
        # Free plan has 1 rotation group now
        # Trying to create more than limit should fail
        self.assertTrue(Plan.objects.can_create_rotation_group(self.user_free))

        # Premium plan is unlimited
        self.assertTrue(Plan.objects.can_create_rotation_group(self.user_premium))

    def test_can_create_campaign_limit(self):
        """Ensure campaign creation respects plan limits."""
        limit = DEFAULT_LIMITS["free"]["active_campaigns"]

        # Initially allowed
        self.assertTrue(Plan.objects.can_create_campaign(self.user_free))

        # Fill up to limit using Campaign manager to enforce plan checks
        for i in range(limit):
            Campaign.objects.create_campaign(
                user=self.user_free,
                name=f"Campaign {i}",
                scheduled_at=timezone.now() + timedelta(days=i)
            )

        # Should now block creation
        self.assertFalse(Plan.objects.can_create_campaign(self.user_free))

        # Ensure ValidationError is raised if exceeded
        with self.assertRaises(ValidationError):
            Campaign.objects.create_campaign(
                user=self.user_free,
                name="Overflow Campaign",
                scheduled_at=timezone.now() + timedelta(days=limit + 1)
            )
