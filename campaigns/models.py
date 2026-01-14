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
        # Count draft + active campaigns toward the plan limit
        plan_limit = Plan.objects.get_limits(getattr(user.plan, "plan_type", "free"))["active_campaigns"]
        if plan_limit is not None:
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

    def __str__(self):
        return f"{self.name} ({self.status})"
