# deliverability/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch
from deliverability.models import DomainCheck, EmailCheck
from deliverability.services import DomainCheckResult, EmailCheckResult

User = get_user_model()


class DeliverabilityTests(TestCase):
    def setUp(self):
        # Create user for authenticated requests
        self.user = User.objects.create_user(
            email="tester@example.com",
            password="pass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # -------------------
    # Domain Tests
    # -------------------
    @patch("deliverability.services.check_domain")
    def test_single_domain_check(self, mock_check_domain):
        """Test domain check API returns correct risk score"""
        mock_check_domain.return_value = DomainCheckResult(
            domain="example.com",
            spf="pass",
            dkim="pass",
            dmarc="fail",
            risk_score=7,
            risk_level="high",
            last_checked="2026-01-12T00:00:00Z"
        )

        response = self.client.post("/deliverability/domains/check/", {"domain": "example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["risk_score"], 7)

    @patch("deliverability.services.check_domain")
    def test_domain_record_created(self, mock_check_domain):
        """Test that a DomainCheck record is created"""
        mock_check_domain.return_value = DomainCheckResult(
            domain="example.org",
            spf="pass",
            dkim="fail",
            dmarc="pass",
            risk_score=4,
            risk_level="medium",
            last_checked="2026-01-12T00:00:00Z"
        )

        response = self.client.post("/deliverability/domains/check/", {"domain": "example.org"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(DomainCheck.objects.filter(domain="example.org", user=self.user).exists())
        check = DomainCheck.objects.get(domain="example.org", user=self.user)
        self.assertEqual(check.risk_level, "medium")

    # -------------------
    # Email Tests
    # -------------------
    @patch("deliverability.services.validate_email_smtp")
    def test_single_email_check(self, mock_validate):
        """Test single email validation"""
        mock_validate.return_value = EmailCheckResult(
            email="valid@example.com",
            status="valid",
            domain_type="free"
        )

        response = self.client.post("/deliverability/emails/check/", {"email": "valid@example.com"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(EmailCheck.objects.filter(email="valid@example.com", user=self.user).exists())

    @patch("deliverability.services.validate_email_smtp")
    def test_bulk_email_check(self, mock_validate):
        """Test bulk email validation"""
        mock_validate.side_effect = lambda email, user=None: EmailCheckResult(
            email=email,
            status="valid",
            domain_type="free"
        )

        emails = ["one@example.com", "two@example.com", "three@example.com"]
        response = self.client.post("/deliverability/emails/bulk-check/", {"emails": emails}, format="json")
        self.assertEqual(response.status_code, 201)

        for email in emails:
            self.assertTrue(EmailCheck.objects.filter(email=email, user=self.user).exists())
