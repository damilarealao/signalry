# campaigns/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Campaign
from datetime import datetime, timedelta


class CampaignForm(forms.ModelForm):
    """Form for creating and editing campaigns."""
    
    schedule_type = forms.ChoiceField(
        choices=[
            ('now', 'Send Now'),
            ('later', 'Schedule for Later'),
        ],
        initial='now',
        widget=forms.RadioSelect(attrs={
            'class': 'space-y-2'
        })
    )
    
    scheduled_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border rounded-md'
        })
    )
    
    scheduled_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full px-3 py-2 border rounded-md'
        })
    )
    
    # ADD THESE FIELDS FOR EMAIL CONTENT
    subject = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'placeholder': 'Email subject line'
        })
    )
    
    body_plain = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border rounded-md h-48',
            'placeholder': 'Plain text version of your email...',
            'rows': 8
        })
    )
    
    body_html = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border rounded-md h-48',
            'placeholder': 'HTML version of your email...',
            'rows': 8
        })
    )
    
    # ADD CONTACT SELECTION
    recipient_type = forms.ChoiceField(
        choices=[
            ('all', 'All Subscribed Contacts'),
            ('group', 'Specific Group'),
            ('custom', 'Custom Selection'),
        ],
        initial='all',
        widget=forms.RadioSelect(attrs={
            'class': 'space-y-2'
        })
    )
    
    contact_group = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border rounded-md'
        })
    )
    
    custom_contacts = forms.ModelMultipleChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'w-full px-3 py-2 border rounded-md h-48'
        })
    )
    
    class Meta:
        model = Campaign
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-md',
                'placeholder': 'e.g., Welcome Email Series, Black Friday Sale'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Set querysets for contact selection
            from message_system.models import ContactGroup, Contact
            self.fields['contact_group'].queryset = ContactGroup.objects.filter(user=self.user)
            
            # FIX: Remove is_active filter to include all subscribed contacts
            self.fields['custom_contacts'].queryset = Contact.objects.filter(
                user=self.user,
                status='subscribed'
                # is_active=True  ← REMOVED THIS FILTER
            )
        
        # Set initial values for schedule fields if editing
        if self.instance and self.instance.pk and self.instance.scheduled_at:
            if self.instance.scheduled_at <= timezone.now() + timedelta(minutes=10):
                self.fields['schedule_type'].initial = 'now'
            else:
                self.fields['schedule_type'].initial = 'later'
                self.fields['scheduled_date'].initial = self.instance.scheduled_at.date()
                self.fields['scheduled_time'].initial = self.instance.scheduled_at.time()
            
            # Get message content if editing
            message = self.instance.messages.first()
            if message:
                self.fields['subject'].initial = message.subject
                self.fields['body_plain'].initial = message.body_plain
                self.fields['body_html'].initial = message.body_html
                
                # Try to determine recipient type
                from message_system.models import MessageRecipient
                # FIX: Count all subscribed contacts, not just active ones
                total_contacts = Contact.objects.filter(
                    user=self.user, 
                    status='subscribed'
                    # is_active=True  ← REMOVED THIS FILTER
                ).count()
                campaign_recipients = message.get_recipient_count()
                
                if campaign_recipients == total_contacts and total_contacts > 0:
                    self.fields['recipient_type'].initial = 'all'
                elif campaign_recipients > 0:
                    # Check if recipients belong to a specific group
                    recipient_contacts = Contact.objects.filter(
                        id__in=message.recipients.values_list('contact', flat=True),
                        user=self.user
                    )
                    
                    # Check if all recipients are in the same group
                    if self.user and recipient_contacts.exists():
                        from django.db.models import Count
                        group_counts = ContactGroup.objects.filter(
                            contacts__in=recipient_contacts,
                            user=self.user
                        ).annotate(
                            recipient_count=Count('contacts')
                        ).filter(recipient_count=campaign_recipients)
                        
                        if group_counts.exists():
                            self.fields['recipient_type'].initial = 'group'
                            self.fields['contact_group'].initial = group_counts.first()
                        else:
                            self.fields['recipient_type'].initial = 'custom'
                            self.fields['custom_contacts'].initial = recipient_contacts
    
    def clean(self):
        """Validate schedule settings and recipient selection."""
        cleaned_data = super().clean()
        
        # Schedule validation
        schedule_type = cleaned_data.get('schedule_type')
        scheduled_date = cleaned_data.get('scheduled_date')
        scheduled_time = cleaned_data.get('scheduled_time')
        
        if schedule_type == 'later':
            if not scheduled_date or not scheduled_time:
                raise ValidationError("Please select both date and time for scheduled sending.")
            
            # Combine date and time
            scheduled_datetime = datetime.combine(scheduled_date, scheduled_time)
            scheduled_datetime = timezone.make_aware(scheduled_datetime)
            
            # Ensure scheduled time is in the future
            if scheduled_datetime < timezone.now():
                raise ValidationError("Scheduled time must be in the future.")
            
            cleaned_data['scheduled_at'] = scheduled_datetime
        else:
            # Send now - schedule for immediate sending (1 minute buffer)
            cleaned_data['scheduled_at'] = timezone.now() + timedelta(minutes=1)
        
        # Recipient validation
        recipient_type = cleaned_data.get('recipient_type', 'all')
        
        if recipient_type == 'group':
            group = cleaned_data.get('contact_group')
            if not group:
                raise ValidationError("Please select a contact group.")
            
            # FIX: Check for subscribed contacts, not necessarily active ones
            contacts = group.get_contacts().filter(status='subscribed')
            if not contacts.exists():
                raise ValidationError(f"The group '{group.name}' has no subscribed contacts.")
                
        elif recipient_type == 'custom':
            contacts = cleaned_data.get('custom_contacts')
            if not contacts:
                raise ValidationError("Please select at least one contact.")
        
        # Email content validation
        subject = cleaned_data.get('subject', '').strip()
        body_plain = cleaned_data.get('body_plain', '').strip()
        
        if not subject:
            raise ValidationError("Email subject is required.")
        
        if not body_plain:
            raise ValidationError("Email body (plain text) is required.")
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the campaign with user, schedule, message, and recipients."""
        campaign = super().save(commit=False)
        campaign.user = self.user
        
        # Set scheduled_at from cleaned data
        campaign.scheduled_at = self.cleaned_data.get('scheduled_at')
        
        # Get schedule_type from cleaned data
        schedule_type = self.cleaned_data.get('schedule_type', 'later')
        
        # If status is not set (new campaign), set initial status
        if not campaign.status:
            # If "Send Now", set status to active immediately
            if schedule_type == 'now':
                campaign.status = 'active'
            else:
                campaign.status = 'draft'
        else:
            # If editing and changing to "Send Now", update status to active
            if schedule_type == 'now' and campaign.status in ['draft', 'paused']:
                campaign.status = 'active'
            # If changing from "Send Now" to "Schedule", revert to draft if not already sent
            elif schedule_type == 'later' and campaign.status == 'active' and campaign.scheduled_at > timezone.now():
                campaign.status = 'draft'
        
        if commit:
            campaign.save()
            
            # Create or update message
            subject = self.cleaned_data.get('subject')
            body_plain = self.cleaned_data.get('body_plain')
            body_html = self.cleaned_data.get('body_html', '')
            
            message = campaign.create_message(
                subject=subject,
                body_plain=body_plain,
                body_html=body_html
            )
            
            # Clear existing recipients (in case we're changing selection)
            message.recipients.all().delete()
            
            # Add recipients based on selection
            recipient_type = self.cleaned_data.get('recipient_type', 'all')
            
            if recipient_type == 'group':
                group = self.cleaned_data.get('contact_group')
                if group:
                    campaign.add_recipients_from_group(group.id)
                    
            elif recipient_type == 'custom':
                contacts = self.cleaned_data.get('custom_contacts')
                if contacts:
                    campaign.add_recipient_contacts([c.id for c in contacts])
                    
            else:  # 'all' - add all subscribed contacts
                from message_system.models import Contact
                # FIX: Include all subscribed contacts, not just active ones
                contacts = Contact.objects.filter(
                    user=self.user,
                    status='subscribed'
                    # is_active=True  ← REMOVED THIS FILTER
                )
                if message and contacts.exists():
                    message.add_recipients(contacts)
        
        return campaign