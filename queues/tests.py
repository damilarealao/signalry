# queues/tests.py
from django.test import TestCase
from unittest.mock import patch
from django.core.management import call_command
from users.models import User
from smtp.models import SMTPAccount
from campaigns.models import Campaign
from message_system.models import Message

class QueueProcessingTests(TestCase):

    def setUp(self):
        # Create a test user (use fields your custom User model accepts)
        self.user = User.objects.create_user(
            email="u@test.com",
            password="password123"
        )

        # Create a dummy SMTP account
        self.smtp = SMTPAccount.objects.create(
            user=self.user,
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="user@test.com",
            smtp_password_encrypted="encryptedpassword",
            status="active"
        )

        # Create a campaign
        self.campaign = Campaign.objects.create(
            user=self.user,
            name="Test Campaign"
        )

        # Create a message in draft
        self.message = Message.objects.create_message(
            campaign=self.campaign,
            subject="Hello",
            body_plain="Test body",
            sender_smtp=self.smtp
        )

        # Mark message as queued for processing
        self.message.status = "queued"
        self.message.save(update_fields=["status"])

    @patch("queues.executor.execute_message_send", return_value=True)
    def test_queued_message_is_sent(self, mock_send):
        """
        Ensure a queued message is processed and marked as sent.
        """
        # Call the management command that runs the queue
        call_command("process_queue")

        # Refresh message from DB
        self.message.refresh_from_db()

        self.assertEqual(self.message.status, "sent")
        self.assertEqual(self.message.retries, 0)
        mock_send.assert_called_once_with(self.message)
