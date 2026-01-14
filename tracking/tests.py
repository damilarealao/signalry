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
        self.user = User.objects.create_user(email="test@example.com", password="pass123")
        # Attach a free plan so campaign creation works
        Plan.objects.create_plan_for_user(self.user, "free")

        self.campaign = Campaign.objects.create_campaign(user=self.user, name="Test")
        self.message = Message.objects.create_message(campaign=self.campaign, subject="Hello")
    
    def test_record_click(self):
        click = Click.objects.create(
            message=self.message,
            beacon_uuid=self.message.uuid,
            url="https://example.com",
            user_agent_family="Chrome"
        )
        self.assertEqual(click.url, "https://example.com")
        self.assertEqual(click.beacon_uuid, self.message.uuid)
