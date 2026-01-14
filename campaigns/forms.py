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
        
        # Set initial values for schedule fields if editing
        if self.instance and self.instance.pk and self.instance.scheduled_at:
            self.fields['schedule_type'].initial = 'later'
            self.fields['scheduled_date'].initial = self.instance.scheduled_at.date()
            self.fields['scheduled_time'].initial = self.instance.scheduled_at.time()
    
    def clean(self):
        """Validate schedule settings."""
        cleaned_data = super().clean()
        
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
            # Send now - schedule for 5 minutes from now to allow for processing
            cleaned_data['scheduled_at'] = timezone.now() + timedelta(minutes=5)
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the campaign with user and schedule."""
        campaign = super().save(commit=False)
        campaign.user = self.user
        
        # Set scheduled_at from cleaned data
        campaign.scheduled_at = self.cleaned_data.get('scheduled_at')
        
        # If status is not set (new campaign), set to draft
        if not campaign.status:
            campaign.status = 'draft'
        
        if commit:
            campaign.save()
        
        return campaign