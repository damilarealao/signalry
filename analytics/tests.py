# analytics/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch

from plans.models import Plan
from campaigns.models import Campaign
from message_system.models import Message, MessageOpen
from smtp.models import SMTPAccount
from deliverability.models import DomainCheck, EmailCheck

User = get_user_model()


class AnalyticsSmokeTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com",
            password="pass123"
        )

        Plan.objects.create_plan_for_user(self.user, "free")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.campaign = Campaign.objects.create_campaign(
            user=self.user,
            name="Test Campaign"
        )

        msg = Message.objects.create_message(
            campaign=self.campaign,
            subject="Hello",
            body_plain="Test body"
        )
        msg.mark_sent()

        MessageOpen.objects.record_open(
            msg,
            raw_ip="1.2.3.4",
            user_agent_family="Chrome"
        )

        with patch("smtp.models.SMTPAccountManager.validate_smtp", return_value=None):
            SMTPAccount.objects.create_smtp(
                user=self.user,
                host="smtp.test.com",
                port=587,
                smtp_user="user@test.com",
                smtp_password="password"
            )

        DomainCheck.objects.create(
            user=self.user,
            domain="example.com",
            spf="pass",
            dkim="pass",
            dmarc="pass"
        )

        EmailCheck.objects.create(
            user=self.user,
            email="test@example.com",
            status="valid"
        )

    def test_campaign_analytics_endpoint(self):
        res = self.client.get(f"/api/campaign/{self.campaign.id}/")
        self.assertEqual(res.status_code, 200)

    def test_user_analytics_me_endpoint(self):
        res = self.client.get("/api/me/")
        self.assertEqual(res.status_code, 200)
