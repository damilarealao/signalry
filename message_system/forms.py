# message_system/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Contact, ContactGroup


class ContactForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=ContactGroup.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    class Meta:
        model = Contact
        fields = ['email', 'first_name', 'last_name', 'phone', 
                 'company', 'notes', 'status', 'tags', 'groups']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'tags': forms.TextInput(attrs={'placeholder': 'comma,separated,tags'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Limit groups to user's groups
            self.fields['groups'].queryset = ContactGroup.objects.filter(user=self.user)
            
            # For existing contact, exclude its own email from uniqueness check
            if self.instance and self.instance.pk:
                self.fields['email'].disabled = True
    
    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        
        # Check for duplicate email for this user
        if self.user:
            qs = Contact.objects.filter(user=self.user, email=email)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise ValidationError(f'A contact with email {email} already exists.')
        
        return email


class ContactGroupForm(forms.ModelForm):
    class Meta:
        model = ContactGroup
        fields = ['name', 'description', 'is_dynamic', 'filter_criteria']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'filter_criteria': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': '{"status": "subscribed", "tags": ["customer", "vip"]}'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_filter_criteria(self):
        criteria = self.cleaned_data.get('filter_criteria', '')
        if criteria and self.cleaned_data.get('is_dynamic', False):
            try:
                # Validate JSON
                import json
                json.loads(criteria)
            except json.JSONDecodeError:
                raise ValidationError('Invalid JSON format for filter criteria.')
        return criteria
    
    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        
        # Check for duplicate name for this user
        if self.user:
            qs = ContactGroup.objects.filter(user=self.user, name=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise ValidationError(f'A group with name "{name}" already exists.')
        
        return name


class ContactImportForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload a CSV file with columns: email, first_name, last_name, phone, company, notes'
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            raise ValidationError('Please upload a CSV file.')
        
        # Check file size (limit to 5MB)
        if csv_file.size > 5 * 1024 * 1024:
            raise ValidationError('File size must be less than 5MB.')
        
        return csv_file