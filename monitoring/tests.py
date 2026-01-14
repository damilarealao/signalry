# monitoring/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from campaigns.models import Campaign
from smtp.models import SMTPAccount
from plans.models import Plan
from monitoring.models import SystemLog, Metric, Alert

User = get_user_model()


class MonitoringSmokeTest(TestCase):
    def setUp(self):
        # -------------------- User --------------------
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="pass123"
        )

        # Assign a free plan so campaign creation works
        Plan.objects.create_plan_for_user(self.user, "free")

        # -------------------- Campaign --------------------
        self.campaign = Campaign.objects.create_campaign(
            user=self.user,
            name="Test Campaign"
        )

        # -------------------- SMTP Account --------------------
        self.smtp = SMTPAccount.objects.create(
            user=self.user,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password_encrypted="encrypted",
        )

    # -------------------- SystemLog Test --------------------
    def test_log_creation(self):
        log = SystemLog.objects.record(
            user=self.user,
            message="Test log message",
            level="info",
            campaign=self.campaign,
            smtp_account=self.smtp
        )
        self.assertEqual(log.level, "info")
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.campaign, self.campaign)
        self.assertEqual(log.smtp_account, self.smtp)
        self.assertIn("Test log", log.message)

    # -------------------- Metric Test --------------------
    def test_metric_creation(self):
        metric = Metric.objects.record(
            user=self.user,
            name="retry_rate",
            value=0.12,
            campaign=self.campaign,
            smtp_account=self.smtp
        )
        self.assertEqual(metric.name, "retry_rate")
        self.assertEqual(metric.value, 0.12)
        self.assertEqual(metric.user, self.user)
        self.assertEqual(metric.campaign, self.campaign)
        self.assertEqual(metric.smtp_account, self.smtp)

    # -------------------- Alert Test --------------------
    def test_alert_creation_and_resolution(self):
        alert = Alert.objects.trigger(
            user=self.user,
            alert_type="failed_campaign",
            message="Campaign failed",
            campaign=self.campaign,
            smtp_account=self.smtp
        )
        self.assertFalse(alert.is_resolved)
        alert.mark_resolved()
        alert.refresh_from_db()
        self.assertTrue(alert.is_resolved)
        self.assertEqual(alert.user, self.user)
        self.assertEqual(alert.campaign, self.campaign)
        self.assertEqual(alert.smtp_account, self.smtp)
