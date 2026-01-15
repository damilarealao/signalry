# tracking/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from message_system.models import Message
from campaigns.models import Campaign
from plans.models import Plan
from .models import Click

User = get_user_model()

class TrackingSmokeTest(TestCase):
    def setUp(self):
        # Create a user
        self.user = User.objects.create_user(email="test@example.com", password="pass123")
        
        # Assign a free plan to satisfy campaign limits
        Plan.objects.create_plan_for_user(self.user, "free")

        # Create a campaign (draft by default)
        self.campaign = Campaign.objects.create_campaign(user=self.user, name="Test Campaign")

        # Create a message linked to the campaign
        self.message = Message.objects.create_message(
            campaign=self.campaign,
            subject="Hello World"
        )
    
    def test_record_click(self):
        # Record a click for tracking
        click = Click.objects.create(
            message=self.message,
            beacon_uuid=self.message.uuid,
            url="https://example.com",
            user_agent_family="Chrome"
        )
        self.assertEqual(click.url, "https://example.com")
        self.assertEqual(click.beacon_uuid, self.message.uuid)
        self.assertEqual(click.message, self.message)
