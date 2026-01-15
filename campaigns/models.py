# campaigns/models.py
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from plans.models import Plan

STATUS_CHOICES = [
    ("draft", "Draft"),
    ("paused", "Paused"),
    ("active", "Active"),
    ("completed", "Completed"),
    ("failed", "Failed"),
]


class CampaignManager(models.Manager):
    def create_campaign(self, user, name, scheduled_at=None, status="draft"):
        """
        Create a campaign while enforcing the user's plan limits.
        Draft status by default. Raises ValidationError if limit exceeded.
        """
        # Use the user's current plan property; fallback to free if none
        user_plan = getattr(user, "current_plan", None)
        plan_type = getattr(user_plan, "plan_type", "free") if user_plan else "free"
        plan_limit = Plan.objects.get_limits(plan_type)["active_campaigns"]

        if plan_limit is not None:
            # Count draft + active campaigns toward the plan limit
            active_count = user.campaigns.filter(status__in=["draft", "active"]).count()
            if active_count >= plan_limit:
                raise ValidationError(
                    "User has reached the maximum number of campaigns for their plan."
                )

        campaign = self.model(
            user=user,
            name=name,
            scheduled_at=scheduled_at or timezone.now(),
            status=status
        )
        campaign.full_clean()
        campaign.save(using=self._db)
        return campaign


class Campaign(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="campaigns"
    )
    name = models.CharField(max_length=255)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CampaignManager()

    def preflight_validate(self):
        """
        Validate campaign before sending.
        Only drafts or paused campaigns can pass preflight.
        """
        if not self.name.strip():
            raise ValidationError("Campaign name cannot be empty.")
        if self.status not in ["draft", "paused"]:
            raise ValidationError(
                "Campaign status must be 'draft' or 'paused' for preflight validation."
            )
        return True
    
    def create_message(self, subject, body_plain="", body_html=""):
        """Create a message for this campaign."""
        from message_system.models import Message
        from smtp.models import SMTPAccount
        
        # Get the user's first active SMTP account
        # FIX: SMTPAccount has 'status' field, not 'is_active' or 'is_default'
        smtp_account = SMTPAccount.objects.filter(
            user=self.user,
            status="active"  # Correct field name
        ).first()
        
        # Check if message already exists for this campaign
        existing_message = self.messages.first()
        if existing_message:
            # Update existing message
            existing_message.subject = subject
            existing_message.body_plain = body_plain
            existing_message.body_html = body_html
            if smtp_account:
                existing_message.sender_smtp = smtp_account
            existing_message.save()
            return existing_message
        
        # Create new message
        message = Message.objects.create_message(
            campaign=self,
            subject=subject,
            body_plain=body_plain,
            body_html=body_html,
            sender_smtp=smtp_account
        )
        return message
    
    def add_recipients_from_group(self, group_id):
        """Add recipients to campaign from a contact group."""
        from message_system.models import MessageRecipient, ContactGroup
        
        try:
            group = ContactGroup.objects.get(id=group_id, user=self.user)
            
            # Get the message (assuming one message per campaign)
            message = self.messages.first()
            if not message:
                return 0
            
            # Get contacts from the group
            # Contact model has 'is_active' field, so this is correct
            contacts = group.get_contacts().filter(status='subscribed', is_active=True)
            
            # Add recipients
            message.add_recipients(contacts)
            
            return contacts.count()
        except ContactGroup.DoesNotExist:
            return 0
    
    def add_recipient_contacts(self, contact_ids):
        """Add specific contacts as recipients."""
        from message_system.models import MessageRecipient, Contact
        
        message = self.messages.first()
        if not message:
            return 0
        
        contacts = Contact.objects.filter(
            id__in=contact_ids,
            user=self.user,
            status='subscribed',
            is_active=True  # Contact model has this field
        )
        
        message.add_recipients(contacts)
        return contacts.count()
    
    def get_recipient_count(self):
        """Get number of recipients for this campaign."""
        message = self.messages.first()
        if message:
            return message.get_recipient_count()
        return 0
    
    def get_sent_count(self):
        """Get number of recipients who have received emails."""
        message = self.messages.first()
        if message:
            return message.get_sent_count()
        return 0
    
    def has_message_content(self):
        """Check if campaign has email content."""
        message = self.messages.first()
        if not message:
            return False
        return bool(message.subject and (message.body_plain or message.body_html))
    
    def has_recipients(self):
        """Check if campaign has recipients."""
        return self.get_recipient_count() > 0
    
    def can_be_sent(self):
        """Check if campaign is ready to be sent."""
        return (
            self.status in ['draft', 'paused'] and
            self.has_message_content() and
            self.has_recipients()
        )

    def __str__(self):
        return f"{self.name} ({self.status})"