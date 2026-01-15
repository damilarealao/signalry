# deliverability/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

CHECK_STATUS_CHOICES = [
    ("pass", "Pass"),
    ("fail", "Fail"),
    ("neutral", "Neutral"),
    ("unknown", "Unknown"),
]

RISK_LEVEL_CHOICES = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
]


class DomainCheck(models.Model):
    """
    Store results of a single domain deliverability check.
    Includes SPF, DKIM, DMARC results and a risk assessment.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="domain_checks",
        null=True,
        blank=True,
    )
    domain = models.CharField(max_length=255)
    spf = models.CharField(max_length=10, choices=CHECK_STATUS_CHOICES, default="unknown")
    dkim = models.CharField(max_length=10, choices=CHECK_STATUS_CHOICES, default="unknown")
    dmarc = models.CharField(max_length=10, choices=CHECK_STATUS_CHOICES, default="unknown")
    risk_score = models.PositiveSmallIntegerField(default=0)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True)
    last_checked = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("domain", "user")
        indexes = [
            models.Index(fields=["domain"]),
            models.Index(fields=["last_checked"]),
        ]

    def __str__(self):
        return f"{self.domain} ({self.risk_level or 'unknown'})"

    def update_risk_level(self):
        """
        Compute risk level based on SPF/DKIM/DMARC results.
        """
        score = 0
        for field in [self.spf, self.dkim, self.dmarc]:
            if field == "pass":
                score += 0
            elif field == "neutral":
                score += 1
            else:  # fail or unknown
                score += 2

        self.risk_score = score
        if score <= 2:
            self.risk_level = "low"
        elif score <= 4:
            self.risk_level = "medium"
        else:
            self.risk_level = "high"
        self.save(update_fields=["risk_score", "risk_level", "updated_at"])


class EmailCheck(models.Model):
    """
    Store results of single email SMTP validation.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_checks")
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=[("valid","Valid"),("invalid","Invalid"),("unknown","Unknown")], default="unknown")
    domain_type = models.CharField(max_length=20, choices=[("free","Free"),("premium","Premium"),("disposable","Disposable")], default="free")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("email", "user")
        indexes = [
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.status})"
