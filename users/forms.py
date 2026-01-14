# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import User

class UserRegistrationForm(UserCreationForm):
    """Form for user registration with email as username."""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        }),
        help_text=_('Required. Enter a valid email address.')
    )
    
    full_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'placeholder': 'Enter your full name (optional)'
        }),
        help_text=_('Optional. Your full name for personalization.')
    )
    
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password'
        }),
        help_text=_('Your password must contain at least 8 characters.')
    )
    
    password2 = forms.CharField(
        label=_("Password Confirmation"),
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        }),
        strip=False,
        help_text=_('Enter the same password as before, for verification.')
    )
    
    class Meta:
        model = User
        fields = ['email', 'full_name', 'password1', 'password2']
    
    def clean_email(self):
        """Validate that email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email.lower()
    
    def save(self, commit=True):
        """Save the user with normalized email."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        user.full_name = self.cleaned_data['full_name']
        
        if commit:
            user.save()
        
        return user

class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form with Tailwind styling."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'placeholder': 'Email address',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information (full name)."""
    
    email_display = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md bg-gray-50',
            'readonly': 'readonly',
            'placeholder': 'Email address'
        }),
        label=_('Email Address'),
        help_text=_('Your email address cannot be changed.')
    )
    
    full_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'placeholder': 'Enter your full name'
        }),
        help_text=_('Your name will be used in welcome messages.')
    )
    
    class Meta:
        model = User
        fields = ['full_name']
    
    def __init__(self, *args, **kwargs):
        """Initialize form with user's current email."""
        super().__init__(*args, **kwargs)
        
        # Set initial value for email display field
        if self.instance and self.instance.email:
            self.fields['email_display'].initial = self.instance.email
        
        # Make email_display field non-editable
        self.fields['email_display'].disabled = True
    
    def clean_full_name(self):
        """Clean and validate full name field."""
        full_name = self.cleaned_data.get('full_name', '').strip()
        
        # Allow empty full name (user can remove their name)
        if not full_name:
            return ''
        
        # Check if name is too short
        if len(full_name) < 2:
            raise ValidationError(_('Name must be at least 2 characters long.'))
        
        # Check if name contains only letters, spaces, hyphens, and apostrophes
        # Remove spaces first for validation
        name_without_spaces = full_name.replace(' ', '').replace('-', '').replace("'", "")
        if not name_without_spaces.isalpha():
            raise ValidationError(_('Name can only contain letters, spaces, hyphens, and apostrophes.'))
        
        return full_name
    
    def save(self, commit=True):
        """Save the user with cleaned full name."""
        user = super().save(commit=False)
        
        # Update full name (already cleaned)
        user.full_name = self.cleaned_data['full_name']
        
        if commit:
            user.save()
        
        return user