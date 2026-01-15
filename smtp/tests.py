# smtp/tests.py
import smtplib
from django.test import TestCase
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
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

    @patch("smtplib.SMTP")
    @patch("smtp.models.decrypt")  # Patch where it's imported in models.py
    def test_get_password_decryption_failure(self, mock_decrypt, mock_smtp):
        """Test that get_password handles decryption failures gracefully."""
        # Mock SMTP for account creation
        instance = MagicMock()
        mock_smtp.return_value = instance
        
        # Mock decrypt to raise an exception
        mock_decrypt.side_effect = Exception("Decryption failed")
        
        # Create an account directly without using create_smtp (which would call encrypt)
        account = SMTPAccount.objects.create(
            user=self.user,
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="mailer@test.com",
            smtp_password_encrypted="some_encrypted_data",
            status="active",
            failure_count=0,
            rotation_group=None
        )
        
        # Test get_password with decryption failure
        password = account.get_password()
        
        # Should return empty string
        self.assertEqual(password, "")
        # Account should be marked as failed
        account.refresh_from_db()
        self.assertEqual(account.status, "failed")
        # decrypt should have been called
        mock_decrypt.assert_called_once_with("some_encrypted_data")

    @patch("smtplib.SMTP")
    @patch("smtp.models.decrypt")  # Patch where it's imported in models.py
    def test_get_password_empty_result(self, mock_decrypt, mock_smtp):
        """Test that get_password handles empty decryption results."""
        # Mock SMTP for account creation
        instance = MagicMock()
        mock_smtp.return_value = instance
        
        # Mock decrypt to return empty string
        mock_decrypt.return_value = ""
        
        # Create an account directly without using create_smtp
        account = SMTPAccount.objects.create(
            user=self.user,
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="mailer@test.com",
            smtp_password_encrypted="some_encrypted_data",
            status="active",
            failure_count=0,
            rotation_group=None
        )
        
        # Test get_password with empty result
        password = account.get_password()
        
        # Should return empty string
        self.assertEqual(password, "")
        # Account should be marked as failed
        account.refresh_from_db()
        self.assertEqual(account.status, "failed")
        # decrypt should have been called
        mock_decrypt.assert_called_once_with("some_encrypted_data")

    @patch("smtplib.SMTP")
    @patch("smtp.models.decrypt")  # Patch where it's imported in models.py
    def test_send_email_with_invalid_password(self, mock_decrypt, mock_smtp):
        """Test that send_email handles invalid passwords gracefully."""
        # Mock SMTP for account creation and sending
        instance = MagicMock()
        mock_smtp.return_value = instance
        
        # Mock decrypt to return empty string (invalid password)
        mock_decrypt.return_value = ""
        
        # Create an account directly
        account = SMTPAccount.objects.create(
            user=self.user,
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="mailer@test.com",
            smtp_password_encrypted="some_encrypted_data",
            status="active",
            failure_count=0,
            rotation_group=None
        )
        
        # Mock SMTP for the send_email call
        send_instance = MagicMock()
        mock_smtp.return_value = send_instance
        
        # Try to send email with invalid password
        with self.assertRaises(ValidationError) as context:
            SMTPAccount.objects.send_email(
                user=self.user,
                to_email="recipient@test.com",
                subject="Hello",
                body="Test email",
                html=False,
                specific_account=account
            )
        
        # Should raise validation error
        self.assertIn("invalid credentials", str(context.exception).lower())
        # Account should be marked as failed
        account.refresh_from_db()
        self.assertEqual(account.status, "failed")
        # decrypt should have been called
        mock_decrypt.assert_called_once_with("some_encrypted_data")

    @patch("smtplib.SMTP")
    def test_test_connection_success(self, mock_smtp):
        """Test the test_connection method with successful connection."""
        instance = MagicMock()
        mock_smtp.return_value = instance
        
        # Create an account - use manager to create properly
        # Mock the SMTP validation in create_smtp
        with patch.object(SMTPAccount.objects, 'validate_smtp'):
            account = SMTPAccount.objects.create_smtp(
                user=self.user,
                host="smtp.test.com",
                port=587,
                smtp_user="mailer@test.com",
                smtp_password="secret123"
            )
        
        # Reset the mock to clear previous calls
        mock_smtp.reset_mock()
        instance.reset_mock()
        
        # Test connection
        success, message = account.test_connection()
        
        # Should succeed
        self.assertTrue(success)
        self.assertEqual(message, "Connection successful")
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with("mailer@test.com", "secret123")
        instance.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_test_connection_authentication_failure(self, mock_smtp):
        """Test the test_connection method with authentication failure."""
        instance = MagicMock()
        # Make login raise authentication error
        instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Authentication failed')
        mock_smtp.return_value = instance
        
        # Create an account - bypass validation for this test
        with patch.object(SMTPAccount.objects, 'validate_smtp'):
            account = SMTPAccount.objects.create_smtp(
                user=self.user,
                host="smtp.test.com",
                port=587,
                smtp_user="mailer@test.com",
                smtp_password="wrongpassword"
            )
        
        # Reset the mock to clear previous calls
        mock_smtp.reset_mock()
        instance.reset_mock()
        
        # Test connection
        success, message = account.test_connection()
        
        # Should fail
        self.assertFalse(success)
        self.assertIn("Authentication failed", message)
        # Failure count should be incremented
        account.refresh_from_db()
        self.assertEqual(account.failure_count, 1)

    def test_str_representation(self):
        """Test the string representation of SMTPAccount."""
        account = SMTPAccount(
            user=self.user,
            smtp_host="smtp.test.com",
            smtp_port=587,
            smtp_user="mailer@test.com",
            smtp_password_encrypted="encrypted_password",
            status="active"
        )
        
        str_repr = str(account)
        self.assertEqual(str_repr, "mailer@test.com@smtp.test.com (active)")