# plans/models.py
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import User

# -------------------- Plan Definitions --------------------
PLAN_CHOICES = [
    ("free", "Free"),
    ("premium", "Premium"),
]

DEFAULT_LIMITS = {
    "free": {
        "smtp_accounts": 1,
        "rotation_groups": 0,
        "daily_send_limit": 500,
        "active_campaigns": 3,
    },
    "premium": {
        "smtp_accounts": None,  # unlimited
        "rotation_groups": None,
        "daily_send_limit": None,
        "active_campaigns": None,
    }
}

# -------------------- Manager --------------------
class PlanManager(models.Manager):
    def create_plan_for_user(self, user, plan_type="free"):
        if plan_type not in dict(PLAN_CHOICES):
            raise ValidationError(f"Invalid plan type: {plan_type}")
        plan = self.model(user=user, plan_type=plan_type)
        plan.full_clean()
        plan.save(using=self._db)
        return plan

    def get_limits(self, plan_type):
        return DEFAULT_LIMITS.get(plan_type, DEFAULT_LIMITS["free"])

    # ---------------- Helpers for enforcement ----------------
    def can_create_smtp(self, user):
        plan = getattr(user, "plan", None)
        if not plan:
            return False  # no plan assigned
        limit = self.get_limits(plan.plan_type)["smtp_accounts"]
        if limit is None:  # unlimited
            return True
        return user.smtp_accounts.count() < limit

    def can_create_rotation_group(self, user):
        plan = getattr(user, "plan", None)
        if not plan:
            return False
        limit = self.get_limits(plan.plan_type)["rotation_groups"]
        if limit is None:
            return True
        rotation_groups = (
            user.smtp_accounts
            .exclude(rotation_group__isnull=True)
            .values_list("rotation_group", flat=True)
            .distinct()
        )
        return rotation_groups.count() < limit

    def can_create_campaign(self, user):
        plan = getattr(user, "plan", None)
        if not plan:
            return False
        limit = self.get_limits(plan.plan_type)["active_campaigns"]
        if limit is None:
            return True
        # Count only active campaigns
        active_count = user.campaigns.filter(status="active").count()
        return active_count < limit

# -------------------- Plan Model --------------------
class Plan(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="plan")
    plan_type = models.CharField(max_length=10, choices=PLAN_CHOICES, default="free")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PlanManager()

    def get_limits(self):
        return self.__class__.objects.get_limits(self.plan_type)

    def __str__(self):
        return f"{self.user.email} -> {self.plan_type}"
