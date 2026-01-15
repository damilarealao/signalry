# message_system/models.py

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from campaigns.models import Campaign
from smtp.models import SMTPAccount
import uuid
import hashlib


STATUS_CHOICES = [
    ("draft", "Draft"),
    ("queued", "Queued"),
    ("sent", "Sent"),
    ("failed", "Failed"),
    ("retried", "Retried"),
]


# -------------------- Contact Manager --------------------
class ContactManager(models.Manager):
    def create_contact(self, user, email, first_name="", last_name="", **extra_fields):
        """
        Create a contact with validation for email uniqueness per user.
        """
        # Normalize email
        email = email.lower().strip()
        
        # Check if contact already exists for this user
        if self.filter(user=user, email=email).exists():
            raise ValidationError(f"Contact with email {email} already exists.")
        
        contact = self.model(
            user=user,
            email=email,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            **extra_fields
        )
        contact.full_clean()
        contact.save(using=self._db)
        return contact
    
    def bulk_create_from_csv(self, user, csv_file):
        """
        Bulk create contacts from CSV file.
        Returns: (success_count, error_count, errors_list)
        """
        import csv
        import io
        
        success_count = 0
        error_count = 0
        errors = []
        
        # Read CSV
        csv_content = csv_file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row_num, row in enumerate(reader, 1):
            try:
                email = row.get('email', '').strip()
                if not email:
                    raise ValidationError("Email is required")
                
                # Create contact
                self.create_contact(
                    user=user,
                    email=email,
                    first_name=row.get('first_name', '').strip(),
                    last_name=row.get('last_name', '').strip(),
                    phone=row.get('phone', '').strip(),
                    company=row.get('company', '').strip(),
                    notes=row.get('notes', '').strip()
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"Row {row_num}: {str(e)}")
        
        return success_count, error_count, errors


# -------------------- Contact Model --------------------
class Contact(models.Model):
    STATUS_CHOICES = [
        ("subscribed", "Subscribed"),
        ("unsubscribed", "Unsubscribed"),
        ("bounced", "Bounced"),
        ("complaint", "Complaint"),
        ("pending", "Pending"),
    ]
    
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="contacts"
    )
    email = models.EmailField(max_length=255)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    company = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="subscribed")
    is_active = models.BooleanField(default=True)
    
    # Tags for segmentation (comma-separated)
    tags = models.CharField(max_length=500, blank=True)
    
    # Groups for segmentation (ManyToMany to ContactGroup)
    groups = models.ManyToManyField(
        "ContactGroup",
        related_name="contacts",
        blank=True
    )
    
    # Import tracking
    import_source = models.CharField(max_length=100, blank=True)
    imported_at = models.DateTimeField(null=True, blank=True)
    
    # GDPR compliance
    subscribed_at = models.DateTimeField(default=timezone.now)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ContactManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'email'],
                name='unique_email_per_user'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.email} ({self.status})"

    def get_full_name(self):
        """Get full name or email if no name provided."""
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.email

    def unsubscribe(self):
        """Mark contact as unsubscribed."""
        self.status = "unsubscribed"
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=['status', 'is_active', 'unsubscribed_at', 'updated_at'])

    def resubscribe(self):
        """Resubscribe a contact."""
        self.status = "subscribed"
        self.is_active = True
        self.unsubscribed_at = None
        self.save(update_fields=['status', 'is_active', 'unsubscribed_at', 'updated_at'])

    def mark_bounced(self):
        """Mark contact as bounced."""
        self.status = "bounced"
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])

    def mark_complaint(self):
        """Mark contact as complaint (spam report)."""
        self.status = "complaint"
        self.is_active = False
        self.save(update_fields=['status', 'is_active', 'updated_at'])

    def add_tag(self, tag):
        """Add a tag to contact."""
        tags = self.get_tags()
        if tag not in tags:
            tags.append(tag)
            self.tags = ','.join(tags)
            self.save(update_fields=['tags', 'updated_at'])

    def remove_tag(self, tag):
        """Remove a tag from contact."""
        tags = self.get_tags()
        if tag in tags:
            tags.remove(tag)
            self.tags = ','.join(tags)
            self.save(update_fields=['tags', 'updated_at'])

    def get_tags(self):
        """Get list of tags."""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []

    def update_last_contacted(self):
        """Update last contacted timestamp."""
        self.last_contacted_at = timezone.now()
        self.save(update_fields=['last_contacted_at', 'updated_at'])


# -------------------- Message Manager --------------------
class MessageManager(models.Manager):
    def create_message(self, campaign, subject, body_plain="", body_html="", sender_smtp=None):
        if not campaign:
            raise ValidationError("Campaign is required to create a message.")

        message = self.model(
            campaign=campaign,
            uuid=str(uuid.uuid4()),
            subject=subject,
            body_plain=body_plain,
            body_html=body_html,
            sender_smtp=sender_smtp,
            status="draft",
            created_at=timezone.now(),
        )
        message.full_clean()
        message.save(using=self._db)
        return message


# -------------------- Message Model --------------------
class Message(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    uuid = models.CharField(max_length=36, unique=True)
    subject = models.CharField(max_length=255)
    body_plain = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    sender_smtp = models.ForeignKey(
        SMTPAccount,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    retries = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MessageManager()

    # -------------------- State transitions --------------------
    def mark_sent(self):
        self.status = "sent"
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "updated_at"])

    def mark_failed(self):
        self.status = "failed"
        self.save(update_fields=["status", "updated_at"])

    def retry(self):
        self.status = "retried"
        self.retries += 1
        self.save(update_fields=["status", "retries", "updated_at"])

    def __str__(self):
        return f"{self.subject} ({self.status})"
    
    def add_recipient(self, contact):
        """Add a recipient to this message."""
        return MessageRecipient.objects.create(message=self, contact=contact)
    
    def add_recipients(self, contacts):
        """Add multiple recipients to this message."""
        recipients = []
        for contact in contacts:
            recipients.append(MessageRecipient(message=self, contact=contact))
        MessageRecipient.objects.bulk_create(recipients)
        return recipients
    
    def get_recipient_count(self):
        """Get number of recipients for this message."""
        return self.recipients.count()
    
    def get_sent_count(self):
        """Get number of recipients who have received this message."""
        return self.recipients.filter(status="sent").count()


# -------------------- MessageRecipient Manager --------------------
class MessageRecipientManager(models.Manager):
    def create_for_message(self, message, contact):
        """Create a recipient for a message."""
        return self.create(message=message, contact=contact)


# -------------------- MessageRecipient Model --------------------
class MessageRecipient(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("opened", "Opened"),
        ("clicked", "Clicked"),
        ("bounced", "Bounced"),
        ("complaint", "Complaint"),
        ("failed", "Failed"),
    ]
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="recipients"
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="message_recipients"
    )
    
    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    
    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MessageRecipientManager()

    class Meta:
        unique_together = ['message', 'contact']
        indexes = [
            models.Index(fields=['message', 'status']),
            models.Index(fields=['contact', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['sent_at']),
        ]

    def __str__(self):
        return f"{self.contact.email} → {self.message.subject} ({self.status})"
    
    def mark_sent(self):
        """Mark as sent."""
        self.status = "sent"
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at', 'updated_at'])
    
    def mark_delivered(self):
        """Mark as delivered."""
        self.status = "delivered"
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at', 'updated_at'])
    
    def mark_opened(self):
        """Mark as opened."""
        self.status = "opened"
        self.opened_at = timezone.now()
        self.save(update_fields=['status', 'opened_at', 'updated_at'])
    
    def mark_clicked(self):
        """Mark as clicked."""
        self.status = "clicked"
        self.clicked_at = timezone.now()
        self.save(update_fields=['status', 'clicked_at', 'updated_at'])
    
    def mark_bounced(self):
        """Mark as bounced."""
        self.status = "bounced"
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_complaint(self):
        """Mark as complaint."""
        self.status = "complaint"
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_failed(self, error_message=""):
        """Mark as failed."""
        self.status = "failed"
        self.error_message = error_message
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'retry_count', 'updated_at'])


# -------------------- MessageOpen Manager --------------------
class MessageOpenManager(models.Manager):
    def record_open(self, message, contact=None, raw_ip=None, user_agent_family="", beacon_uuid=None):
        """
        Canonical entry point for recording opens.
        All privacy rules enforced here.
        """
        if beacon_uuid is None:
            beacon_uuid = message.uuid
        
        # Try to find the recipient if contact is provided
        recipient = None
        if contact:
            recipient = MessageRecipient.objects.filter(
                message=message, 
                contact=contact
            ).first()
        
        ip_hash = None
        if raw_ip:
            ip_hash = hashlib.sha256(raw_ip.encode("utf-8")).hexdigest()

        if user_agent_family:
            user_agent_family = user_agent_family.split("/")[0][:50]
        
        # Update recipient status if found
        if recipient:
            recipient.mark_opened()

        return self.create(
            message=message,
            recipient=recipient,
            beacon_uuid=beacon_uuid,
            ip_hash=ip_hash,
            user_agent_family=user_agent_family,
            opened_at=timezone.now(),
        )


# -------------------- MessageOpen Model --------------------
class MessageOpen(models.Model):
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="opens"
    )
    recipient = models.ForeignKey(
        MessageRecipient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opens"
    )
    beacon_uuid = models.CharField(max_length=36)
    ip_hash = models.CharField(max_length=64, blank=True, null=True)
    user_agent_family = models.CharField(max_length=50, blank=True)
    opened_at = models.DateTimeField(default=timezone.now)

    objects = MessageOpenManager()

    class Meta:
        indexes = [
            models.Index(fields=["beacon_uuid"]),
            models.Index(fields=["opened_at"]),
            models.Index(fields=["message", "recipient"]),
        ]

    def save(self, *args, **kwargs):
        # Defensive layer: ensure UA is coarse even if misused
        if self.user_agent_family:
            self.user_agent_family = self.user_agent_family.split("/")[0][:50]
        super().save(*args, **kwargs)

    def __str__(self):
        recipient_email = self.recipient.contact.email if self.recipient else "Unknown"
        return f"Open for {recipient_email} at {self.opened_at}"


# -------------------- ContactGroup Model --------------------
class ContactGroup(models.Model):
    """
    Groups for segmenting contacts (like "Customers", "Newsletter", "VIP", etc.)
    """
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="contact_groups"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Filter criteria (stored as JSON for flexibility)
    filter_criteria = models.JSONField(default=dict, blank=True)
    
    # Auto-update tracking
    is_dynamic = models.BooleanField(default=False)
    last_updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_group_name_per_user'
            )
        ]

    def __str__(self):
        return f"{self.name} ({'Dynamic' if self.is_dynamic else 'Static'})"

    def get_contacts(self):
        """Get contacts in this group."""
        if self.is_dynamic:
            # Apply filter criteria to get contacts dynamically
            from django.db.models import Q
            query = Q(user=self.user, is_active=True)
            
            # Apply filters from criteria
            criteria = self.filter_criteria
            
            if 'status' in criteria:
                query &= Q(status=criteria['status'])
            
            if 'tags' in criteria and criteria['tags']:
                # Filter by tags (contacts with any of the tags)
                tags = criteria['tags']
                tag_query = Q()
                for tag in tags:
                    tag_query |= Q(tags__icontains=tag)
                query &= tag_query
            
            if 'created_after' in criteria:
                query &= Q(created_at__gte=criteria['created_after'])
            
            return Contact.objects.filter(query)
        else:
            # Static group - use many-to-many relationship
            return self.contacts.all()

    def update_dynamic_members(self):
        """Update dynamic group membership based on criteria."""
        if self.is_dynamic:
            # Clear existing static memberships
            self.contacts.clear()
            
            # Get contacts matching criteria
            matching_contacts = self.get_contacts()
            
            # Add them to the group
            for contact in matching_contacts:
                self.contacts.add(contact)
            
            return matching_contacts.count()
        return 0