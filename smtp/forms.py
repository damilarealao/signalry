# smtp/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import SMTPAccount
import smtplib


class SMTPAccountForm(forms.ModelForm):
    """Form for creating/editing SMTP accounts."""
    
    smtp_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border rounded-md',
            'placeholder': 'Enter SMTP password',
            'autocomplete': 'new-password'
        }),
        help_text="Your SMTP server password",
        required=False  # Make optional initially
    )
    
    class Meta:
        model = SMTPAccount
        fields = ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'rotation_group']
        widgets = {
            'smtp_host': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-md',
                'placeholder': 'smtp.gmail.com'
            }),
            'smtp_port': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-md',
                'placeholder': '587'
            }),
            'smtp_user': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-md',
                'placeholder': 'your-email@gmail.com'
            }),
            'rotation_group': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border rounded-md',
                'placeholder': 'default (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # If creating new account, password is required
        if not self.instance or not self.instance.pk:
            self.fields['smtp_password'].required = True
            self.fields['smtp_password'].help_text = "Your SMTP server password"
        else:
            # Editing existing account - password is optional
            self.fields['smtp_password'].required = False
            self.fields['smtp_password'].help_text = "Leave empty to keep current password"
            self.fields['smtp_password'].widget.attrs['placeholder'] = "Leave empty to keep current"
    
    def clean(self):
        """Validate SMTP credentials by testing the connection."""
        cleaned_data = super().clean()
        
        # Only test connection if all required fields are present
        if all(k in cleaned_data for k in ['smtp_host', 'smtp_port', 'smtp_user']):
            host = cleaned_data['smtp_host']
            port = cleaned_data['smtp_port']
            username = cleaned_data['smtp_user']
            password = cleaned_data.get('smtp_password')
            
            # If editing and password not provided, try to get existing one
            if self.instance and self.instance.pk and not password:
                try:
                    password = self.instance.get_password()
                    # If decryption fails, get_password() will return empty string
                    # and we need to ask for a new password
                    if not password:
                        raise ValidationError({
                            'smtp_password': "Cannot decrypt existing password. Please enter a new SMTP password."
                        })
                except Exception as e:
                    # If any error occurs during decryption
                    raise ValidationError({
                        'smtp_password': f"Cannot access existing password: {str(e)}. Please enter a new password."
                    })
            
            # If we still don't have a password, it's an error
            if not password:
                if self.instance and self.instance.pk:
                    # Editing without password and couldn't get existing one
                    raise ValidationError({
                        'smtp_password': "Password is required. Please enter your SMTP password."
                    })
                else:
                    # Creating new account without password
                    raise ValidationError({
                        'smtp_password': "Password is required for new SMTP accounts."
                    })
            
            # Test the connection with the password
            try:
                # Test SMTP connection
                server = smtplib.SMTP(host, port, timeout=10)
                server.starttls()
                server.login(username, password)
                server.quit()
            except smtplib.SMTPAuthenticationError:
                raise ValidationError("Authentication failed. Check your username and password.")
            except smtplib.SMTPException as e:
                raise ValidationError(f"SMTP connection failed: {str(e)}")
            except Exception as e:
                raise ValidationError(f"Connection error: {str(e)}")
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the SMTP account with encrypted password."""
        smtp_account = super().save(commit=False)
        smtp_account.user = self.user
        
        # Update password only if provided (for new accounts or password changes)
        if self.cleaned_data.get('smtp_password'):
            from core.encryption import encrypt
            try:
                smtp_account.smtp_password_encrypted = encrypt(self.cleaned_data['smtp_password'])
            except Exception as e:
                raise ValidationError(f"Failed to encrypt password: {str(e)}")
        # If editing and password not provided, keep existing encrypted password
        # The encrypted field is already set on the instance
        
        if commit:
            smtp_account.save()
        
        return smtp_account