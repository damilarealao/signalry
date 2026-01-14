# message_system/tests.py
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from users.models import User
from smtp.models import SMTPAccount
from plans.models import Plan
from campaigns.models import Campaign
from .models import Message, MessageOpen
import hashlib
from rest_framework.test import APIClient


class MessageBeaconTests(TestCase):
    """Combined tests for Message model, MessageOpen, and Beacon tracking."""

    def setUp(self):
        """Set up users, plans, SMTP account, campaign, and message."""
        # Patch SMTP inside setup
        patcher = patch("smtp.models.smtplib.SMTP")
        self.mock_smtp = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_smtp.return_value = MagicMock()

        # Users
        self.user_free = User.objects.create_user(
            email="free@test.com",
            password="pass123",
        )
        self.user_premium = User.objects.create_user(
            email="premium@test.com",
            password="pass123",
        )

        # Plans
        Plan.objects.create_plan_for_user(self.user_free, "free")
        Plan.objects.create_plan_for_user(self.user_premium, "premium")

        # SMTP account
        self.smtp_account = SMTPAccount.objects.create_smtp(
            user=self.user_free,
            host="smtp.test.com",
            port=587,
            smtp_user="user@test.com",
            smtp_password="pass123",
        )

        # Campaign
        self.campaign = Campaign.objects.create_campaign(
            user=self.user_free,
            name="Test Campaign",
            scheduled_at=timezone.now(),
        )

        # Message
        self.message = Message.objects.create_message(
            campaign=self.campaign,
            subject="Beacon Test",
            body_html="<p>Hello</p>",
            sender_smtp=self.smtp_account,
        )

        # API client for beacon endpoint
        self.client = APIClient()

    # -------------------- Message Tests --------------------
    def test_creation_without_campaign_raises_error(self):
        """Cannot create a message without a campaign."""
        with self.assertRaises(ValidationError):
            Message.objects.create_message(
                campaign=None,
                subject="No Campaign",
                body_plain="This should fail",
                sender_smtp=self.smtp_account,
            )

    def test_message_creation_and_unique_uuid(self):
        """Message should be created with draft status and unique UUID."""
        uuids = set()
        for i in range(3):
            msg = Message.objects.create_message(
                campaign=self.campaign,
                subject=f"Message {i}",
                body_plain=f"Plain {i}",
                sender_smtp=self.smtp_account,
            )
            self.assertEqual(msg.status, "draft")
            self.assertIsNotNone(msg.uuid)
            self.assertNotIn(msg.uuid, uuids)
            uuids.add(msg.uuid)

    def test_status_transitions(self):
        """Mark message sent, failed, and retried updates fields correctly."""
        msg = self.message

        msg.mark_sent()
        self.assertEqual(msg.status, "sent")
        self.assertIsNotNone(msg.sent_at)

        msg.mark_failed()
        self.assertEqual(msg.status, "failed")

        msg.retry()
        self.assertEqual(msg.status, "retried")
        self.assertEqual(msg.retries, 1)

    # -------------------- MessageOpen Tests --------------------
    def test_message_open_creation_and_privacy(self):
        """Ensure MessageOpen is recorded with hashed IP and coarse user-agent."""
        raw_ip = "192.168.1.100"
        open_event = MessageOpen.objects.record_open(
            message=self.message,
            raw_ip=raw_ip,
            user_agent_family="Firefox/123.45",
        )
        expected_hash = hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()
        self.assertEqual(open_event.ip_hash, expected_hash)
        self.assertEqual(open_event.user_agent_family, "Firefox")
        self.assertIsNotNone(open_event.opened_at)

    def test_multiple_opens_same_message(self):
        """Ensure multiple opens for the same message can be recorded."""
        ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
        opens = []

        for ip in ips:
            mo = MessageOpen.objects.record_open(
                message=self.message,
                raw_ip=ip,
                user_agent_family="Chrome/100",
            )
            opens.append(mo)

        self.assertEqual(MessageOpen.objects.filter(message=self.message).count(), 3)

        for i, mo in enumerate(opens):
            expected_hash = hashlib.sha256(ips[i].encode("utf-8")).hexdigest()
            self.assertEqual(mo.ip_hash, expected_hash)
            self.assertEqual(mo.user_agent_family, "Chrome")

    # -------------------- Beacon Endpoint Tests --------------------
    def test_beacon_creates_open_event(self):
        """Visiting the tracking pixel records a MessageOpen event."""
        url = f"/api/t/{self.message.uuid}.png"
        response = self.client.get(
            url,
            HTTP_USER_AGENT="Chrome/120.0",
            REMOTE_ADDR="123.123.123.123"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

        opens = MessageOpen.objects.filter(message=self.message)
        self.assertEqual(opens.count(), 1)

        open_event = opens.first()
        expected_hash = hashlib.sha256("123.123.123.123".encode("utf-8")).hexdigest()
        self.assertEqual(open_event.ip_hash, expected_hash)
        self.assertEqual(open_event.user_agent_family, "Chrome")

    def test_beacon_invalid_uuid_does_not_crash(self):
        """Requesting a non-existent UUID returns 200 PNG without errors."""
        url = "/api/t/00000000-0000-0000-0000-000000000000.png"
        response = self.client.get(
            url,
            HTTP_USER_AGENT="Chrome/120.0",
            REMOTE_ADDR="1.1.1.1"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(MessageOpen.objects.count(), 0)
