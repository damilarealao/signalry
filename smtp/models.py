#smtp/models.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.encryption import encrypt, decrypt
from users.models import User
import random

STATUS_CHOICES = [
    ("active", "Active"),
    ("disabled", "Disabled"),
    ("failed", "Failed"),
]

class SMTPAccountManager(models.Manager):

    def validate_smtp(self, host, port, smtp_user, smtp_password):
        """Test SMTP connection and authentication before saving."""
        try:
            server = smtplib.SMTP(host, port, timeout=5)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.quit()
        except Exception as e:
            raise ValidationError(f"SMTP test failed: {e}")

    def create_smtp(self, user, host, port, smtp_user, smtp_password, rotation_group=None):
        """Create and validate an SMTP account."""
        # Test SMTP credentials first
        self.validate_smtp(host, port, smtp_user, smtp_password)

        account = self.model(
            user=user,
            smtp_host=host,
            smtp_port=port,
            smtp_user=smtp_user,
            smtp_password_encrypted=encrypt(smtp_password),
            rotation_group=rotation_group,
            status="active",
            last_health_check=timezone.now(),
            failure_count=0
        )
        account.full_clean()
        account.save(using=self._db)
        return account

    def disable_if_failed(self, smtp_account, failure_threshold=3):
        """Automatically disable account if failures exceed threshold."""
        if smtp_account.failure_count >= failure_threshold:
            smtp_account.status = "disabled"
            smtp_account.save(update_fields=["status"])
            return True
        return False

    def get_smtp_for_sending(self, user, rotation_group=None, specific_account=None):
        """
        Return an SMTP account for sending.
        - If `specific_account` is provided, use it.
        - Otherwise, pick a random active account from `rotation_group`.
        """
        if specific_account:
            if specific_account.status != "active":
                raise ValidationError("Selected SMTP account is not active")
            return specific_account

        qs = self.filter(user=user, status="active")
        if rotation_group:
            qs = qs.filter(rotation_group=rotation_group)

        accounts = list(qs)
        if not accounts:
            raise ValidationError("No active SMTP accounts available for sending")
        return random.choice(accounts)

    def send_email(self, user, to_email, subject, body, html=False, rotation_group=None, specific_account=None):
        """
        Send an email using a chosen SMTP.
        - `html=True` sends HTML content, otherwise plain text.
        """
        smtp_account = self.get_smtp_for_sending(user, rotation_group, specific_account)
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_account.smtp_user
            msg['To'] = to_email
            msg['Subject'] = subject

            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_account.smtp_host, smtp_account.smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_account.smtp_user, smtp_account.get_password())
            server.sendmail(smtp_account.smtp_user, to_email, msg.as_string())
            server.quit()

            # Reset failure count on success
            smtp_account.reset_failures()
            return True

        except Exception:
            smtp_account.mark_failure()
            raise

class SMTPAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="smtp_accounts")
    smtp_host = models.CharField(max_length=255)
    smtp_port = models.PositiveIntegerField()
    smtp_user = models.CharField(max_length=255)
    smtp_password_encrypted = models.TextField()
    rotation_group = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    last_health_check = models.DateTimeField(blank=True, null=True)
    failure_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SMTPAccountManager()

    def get_password(self):
        return decrypt(self.smtp_password_encrypted)

    def mark_failure(self):
        """Increment failure counter and auto-disable if needed."""
        self.failure_count += 1
        self.last_health_check = timezone.now()
        self.save(update_fields=["failure_count", "last_health_check"])
        self.__class__.objects.disable_if_failed(self)

    def reset_failures(self):
        """Reset failure count and restore active status."""
        self.failure_count = 0
        self.status = "active"
        self.last_health_check = timezone.now()
        self.save(update_fields=["failure_count", "status", "last_health_check"])

    def __str__(self):
        return f"{self.smtp_user}@{self.smtp_host} ({self.status})"
