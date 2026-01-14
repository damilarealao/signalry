# smtp/tests.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from users.models import User
from .models import SMTPAccount

class SMTPAccountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass123")

    @patch("smtplib.SMTP")
    def test_create_smtp_account(self, mock_smtp):
        # Mock SMTP instance
        instance = MagicMock()
        mock_smtp.return_value = instance

        account = SMTPAccount.objects.create_smtp(
            user=self.user,
            host="smtp.test.com",
            port=587,
            smtp_user="mailer@test.com",
            smtp_password="secret123",
            rotation_group="default"
        )
        self.assertEqual(account.user, self.user)
        self.assertEqual(account.status, "active")
        self.assertEqual(account.get_password(), "secret123")
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with("mailer@test.com", "secret123")
        instance.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_failure_increment_and_auto_disable(self, mock_smtp):
        instance = MagicMock()
        mock_smtp.return_value = instance

        account = SMTPAccount.objects.create_smtp(
            user=self.user,
            host="smtp.test.com",
            port=587,
            smtp_user="mailer@test.com",
            smtp_password="secret123"
        )
        for _ in range(3):
            account.mark_failure()
        self.assertEqual(account.status, "disabled")
        self.assertEqual(account.failure_count, 3)

    @patch("smtplib.SMTP")
    def test_reset_failures(self, mock_smtp):
        instance = MagicMock()
        mock_smtp.return_value = instance

        account = SMTPAccount.objects.create_smtp(
            user=self.user,
            host="smtp.test.com",
            port=587,
            smtp_user="mailer@test.com",
            smtp_password="secret123"
        )
        for _ in range(2):
            account.mark_failure()
        account.reset_failures()
        self.assertEqual(account.failure_count, 0)
        self.assertEqual(account.status, "active")

    @patch("smtplib.SMTP")
    def test_send_with_specific_smtp(self, mock_smtp):
        instance = MagicMock()
        mock_smtp.return_value = instance

        account = SMTPAccount.objects.create_smtp(
            user=self.user,
            host="smtp.test.com",
            port=587,
            smtp_user="mailer@test.com",
            smtp_password="secret123"
        )
        result = SMTPAccount.objects.send_email(
            user=self.user,
            to_email="recipient@test.com",
            subject="Hello",
            body="Test email",
            html=False,
            specific_account=account
        )
        self.assertTrue(result)
        instance.sendmail.assert_called_once()

    @patch("smtplib.SMTP")
    def test_smtp_rotation_selection(self, mock_smtp):
        instance = MagicMock()
        mock_smtp.return_value = instance

        accounts = [
            SMTPAccount.objects.create_smtp(
                user=self.user,
                host=f"smtp{i}.test.com",
                port=587,
                smtp_user=f"mailer{i}@test.com",
                smtp_password="secret123",
                rotation_group="group1"
            ) for i in range(3)
        ]

        # Sending email using rotation group
        result = SMTPAccount.objects.send_email(
            user=self.user,
            to_email="recipient@test.com",
            subject="Rotation Test",
            body="Testing rotation",
            html=False,
            rotation_group="group1"
        )
        self.assertTrue(result)
        instance.sendmail.assert_called_once()
