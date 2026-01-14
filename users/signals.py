# users/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User


@receiver(post_save, sender=User)
def set_default_permissions(sender, instance, created, **kwargs):
    """Set default permissions based on plan"""
    if created:
        # Set default permissions based on plan
        if instance.plan == 'free':
            instance.permissions = ['can_send_emails', 'can_validate_emails']
        elif instance.plan == 'premium':
            instance.permissions = [
                'can_send_emails',
                'can_validate_emails',
                'can_schedule',
                'can_use_advanced_analytics',
                'can_rotate_smtp'
            ]
        
        # Save only permissions to avoid recursion
        User.objects.filter(pk=instance.pk).update(permissions=instance.permissions)