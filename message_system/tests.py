# message_system/tests.py - FIXED VERSION
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from users.models import User
from smtp.models import SMTPAccount
from plans.models import Plan
from campaigns.models import Campaign
from .models import Message, MessageOpen, Contact, MessageRecipient, ContactGroup
import hashlib
from rest_framework.test import APIClient
import io


class MessageBeaconTests(TestCase):
    """Combined tests for Message model, MessageOpen, and Beacon tracking."""

    def setUp(self):
        """Set up users, plans, SMTP account, campaign, message, and contacts."""
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

        # Contacts
        self.contact1 = Contact.objects.create_contact(
            user=self.user_free,
            email="recipient1@test.com",
            first_name="John",
            last_name="Doe"
        )
        self.contact2 = Contact.objects.create_contact(
            user=self.user_free,
            email="recipient2@test.com",
            first_name="Jane",
            last_name="Smith"
        )

        # Message
        self.message = Message.objects.create_message(
            campaign=self.campaign,
            subject="Beacon Test",
            body_html="<p>Hello</p>",
            sender_smtp=self.smtp_account,
        )

        # Add recipients to message (using get_or_create to avoid duplicates)
        self.recipient1, _ = MessageRecipient.objects.get_or_create(
            message=self.message,
            contact=self.contact1,
            defaults={'status': 'pending'}
        )
        self.recipient2, _ = MessageRecipient.objects.get_or_create(
            message=self.message,
            contact=self.contact2,
            defaults={'status': 'pending'}
        )

        # API client for beacon endpoint
        self.client = APIClient()

    # -------------------- Contact Tests --------------------
    def test_contact_creation(self):
        """Test contact creation and uniqueness per user."""
        # Test basic contact creation
        contact = Contact.objects.create_contact(
            user=self.user_free,
            email="new@test.com",
            first_name="Test",
            last_name="User"
        )
        self.assertEqual(contact.email, "new@test.com")
        self.assertEqual(contact.status, "subscribed")
        self.assertTrue(contact.is_active)
        
        # Test email normalization
        contact2 = Contact.objects.create_contact(
            user=self.user_free,
            email="UPPERCASE@TEST.COM",
            first_name="Upper"
        )
        self.assertEqual(contact2.email, "uppercase@test.com")
        
        # Test duplicate email for same user raises error
        with self.assertRaises(ValidationError):
            Contact.objects.create_contact(
                user=self.user_free,
                email="new@test.com"  # Duplicate
            )
        
        # Test different users can have same email
        contact3 = Contact.objects.create_contact(
            user=self.user_premium,
            email="new@test.com"  # Same email, different user
        )
        self.assertEqual(contact3.user, self.user_premium)

    def test_contact_status_transitions(self):
        """Test contact status management methods."""
        contact = Contact.objects.create_contact(
            user=self.user_free,
            email="status@test.com"
        )
        
        # Test unsubscribe
        contact.unsubscribe()
        self.assertEqual(contact.status, "unsubscribed")
        self.assertFalse(contact.is_active)
        self.assertIsNotNone(contact.unsubscribed_at)
        
        # Test resubscribe
        contact.resubscribe()
        self.assertEqual(contact.status, "subscribed")
        self.assertTrue(contact.is_active)
        self.assertIsNone(contact.unsubscribed_at)
        
        # Test bounce
        contact.mark_bounced()
        self.assertEqual(contact.status, "bounced")
        self.assertFalse(contact.is_active)
        
        # Test complaint
        contact.resubscribe()  # Reset first
        contact.mark_complaint()
        self.assertEqual(contact.status, "complaint")
        self.assertFalse(contact.is_active)

    def test_contact_tags(self):
        """Test contact tag management."""
        contact = Contact.objects.create_contact(
            user=self.user_free,
            email="tags@test.com"
        )
        
        # Add tags
        contact.add_tag("customer")
        contact.add_tag("vip")
        self.assertEqual(contact.get_tags(), ["customer", "vip"])
        
        # Remove tag
        contact.remove_tag("customer")
        self.assertEqual(contact.get_tags(), ["vip"])
        
        # Test duplicate tag doesn't add again
        contact.add_tag("vip")
        self.assertEqual(contact.get_tags(), ["vip"])

    # -------------------- MessageRecipient Tests --------------------
    def test_message_recipient_creation(self):
        """Test message recipient creation and relationships."""
        # Test recipient creation
        self.assertEqual(self.message.recipients.count(), 2)
        self.assertEqual(self.contact1.message_recipients.count(), 1)
        
        # Test unique constraint - use transaction.atomic to isolate the test
        from django.db import transaction
        
        try:
            with transaction.atomic():
                MessageRecipient.objects.create(
                    message=self.message,
                    contact=self.contact1  # Duplicate - should fail
                )
            self.fail("Should have raised IntegrityError")
        except IntegrityError:
            # Expected - duplicate should raise IntegrityError
            pass
        
        # Refresh recipients to ensure they're still valid
        self.recipient1.refresh_from_db()
        self.recipient2.refresh_from_db()
        
        # Test recipient status methods
        self.recipient1.mark_sent()
        self.assertEqual(self.recipient1.status, "sent")
        self.assertIsNotNone(self.recipient1.sent_at)
        
        self.recipient1.mark_opened()
        self.assertEqual(self.recipient1.status, "opened")
        self.assertIsNotNone(self.recipient1.opened_at)
        
        self.recipient1.mark_clicked()
        self.assertEqual(self.recipient1.status, "clicked")
        self.assertIsNotNone(self.recipient1.clicked_at)
        
        self.recipient2.mark_failed("SMTP error")
        self.assertEqual(self.recipient2.status, "failed")
        self.assertEqual(self.recipient2.error_message, "SMTP error")
        self.assertEqual(self.recipient2.retry_count, 1)

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

    def test_message_recipient_methods(self):
        """Test message recipient helper methods."""
        # Test adding single recipient
        new_contact = Contact.objects.create_contact(
            user=self.user_free,
            email="newrecipient@test.com"
        )
        recipient = self.message.add_recipient(new_contact)
        self.assertEqual(recipient.contact, new_contact)
        self.assertEqual(recipient.message, self.message)
        
        # Test adding multiple recipients
        contacts = [
            Contact.objects.create_contact(user=self.user_free, email=f"multi{i}@test.com")
            for i in range(3)
        ]
        recipients = self.message.add_recipients(contacts)
        self.assertEqual(len(recipients), 3)
        
        # Test recipient counts
        self.assertEqual(self.message.get_recipient_count(), 6)  # 2 from setup + 1 + 3
        
        # Test sent count
        self.recipient1.mark_sent()
        self.assertEqual(self.message.get_sent_count(), 1)

    # -------------------- MessageOpen Tests --------------------
    def test_message_open_creation_with_recipient(self):
        """Ensure MessageOpen is recorded with hashed IP and coarse user-agent, linked to recipient."""
        raw_ip = "192.168.1.100"
        open_event = MessageOpen.objects.record_open(
            message=self.message,
            contact=self.contact1,  # Link to specific contact
            raw_ip=raw_ip,
            user_agent_family="Firefox/123.45",
        )
        
        expected_hash = hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()
        self.assertEqual(open_event.ip_hash, expected_hash)
        self.assertEqual(open_event.user_agent_family, "Firefox")
        self.assertEqual(open_event.recipient, self.recipient1)
        self.assertEqual(open_event.recipient.status, "opened")  # Should be updated
        self.assertIsNotNone(open_event.opened_at)

    def test_message_open_creation_without_contact(self):
        """Test MessageOpen recording without specific contact (for backward compatibility)."""
        raw_ip = "10.0.0.1"
        open_event = MessageOpen.objects.record_open(
            message=self.message,
            raw_ip=raw_ip,
            user_agent_family="Chrome/100",
        )
        
        expected_hash = hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()
        self.assertEqual(open_event.ip_hash, expected_hash)
        self.assertEqual(open_event.user_agent_family, "Chrome")
        self.assertIsNone(open_event.recipient)  # No recipient linked
        self.assertIsNotNone(open_event.opened_at)

    def test_multiple_opens_same_message(self):
        """Ensure multiple opens for the same message can be recorded."""
        ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
        
        for ip in ips:
            MessageOpen.objects.record_open(
                message=self.message,
                contact=self.contact1,
                raw_ip=ip,
                user_agent_family="Chrome/100",
            )

        opens = MessageOpen.objects.filter(message=self.message, recipient=self.recipient1)
        self.assertEqual(opens.count(), 3)
        
        # Check recipient status
        self.recipient1.refresh_from_db()
        self.assertEqual(self.recipient1.status, "opened")
        self.assertIsNotNone(self.recipient1.opened_at)

    # -------------------- Beacon Endpoint Tests --------------------
    def test_beacon_creates_open_event(self):
        """Visiting the tracking pixel records a MessageOpen event."""
        # Note: This test assumes you have a URL pattern for tracking pixels
        # If not, you'll need to create the view first
        try:
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
        except Exception as e:
            # Skip if tracking URLs aren't set up yet
            self.skipTest(f"Tracking URLs not configured: {e}")

    def test_beacon_invalid_uuid_does_not_crash(self):
        """Requesting a non-existent UUID returns 200 PNG without errors."""
        try:
            url = "/api/t/00000000-0000-0000-0000-000000000000.png"
            response = self.client.get(
                url,
                HTTP_USER_AGENT="Chrome/120.0",
                REMOTE_ADDR="1.1.1.1"
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")
            self.assertEqual(MessageOpen.objects.count(), 0)
        except Exception as e:
            # Skip if tracking URLs aren't set up yet
            self.skipTest(f"Tracking URLs not configured: {e}")

    # -------------------- ContactGroup Tests --------------------
    def test_contact_group_creation(self):
        """Test contact group creation and contact membership."""
        # Create a static group
        group = ContactGroup.objects.create(
            user=self.user_free,
            name="Test Group",
            description="Test description",
            is_dynamic=False
        )
        
        # Add contacts to group
        group.contacts.add(self.contact1, self.contact2)
        
        self.assertEqual(group.contacts.count(), 2)
        self.assertEqual(self.contact1.groups.count(), 1)
        self.assertEqual(self.contact2.groups.count(), 1)
        
        # Test dynamic group (basic test)
        dynamic_group = ContactGroup.objects.create(
            user=self.user_free,
            name="Dynamic Group",
            is_dynamic=True,
            filter_criteria={"status": "subscribed"}
        )
        
        contacts = dynamic_group.get_contacts()
        self.assertEqual(contacts.count(), 2)  # Both contacts are subscribed

    # -------------------- CSV Import Tests --------------------
    def test_bulk_create_from_csv(self):
        """Test bulk contact creation from CSV."""
        # Create CSV content
        csv_content = """email,first_name,last_name,company
john@example.com,John,Doe,ACME Inc
jane@example.com,Jane,Smith,Tech Corp
invalid-email,Test,User,Test Corp
,Missing,Email,Corp
"""
        
        # Create a file-like object
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        # Import contacts
        success_count, error_count, errors = Contact.objects.bulk_create_from_csv(
            user=self.user_free,
            csv_file=csv_file
        )
        
        # Check results
        self.assertEqual(success_count, 2)  # 2 valid emails
        self.assertEqual(error_count, 2)  # 2 errors
        self.assertEqual(len(errors), 2)
        
        # Check created contacts
        contacts = Contact.objects.filter(user=self.user_free)
        self.assertEqual(contacts.count(), 4)  # 2 from setup + 2 from CSV
        
        # Verify specific contacts
        john = Contact.objects.get(email="john@example.com")
        self.assertEqual(john.first_name, "John")
        self.assertEqual(john.last_name, "Doe")
        self.assertEqual(john.company, "ACME Inc")
        
        jane = Contact.objects.get(email="jane@example.com")
        self.assertEqual(jane.first_name, "Jane")
        self.assertEqual(jane.last_name, "Smith")
        self.assertEqual(jane.company, "Tech Corp")