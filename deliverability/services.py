# deliverability/services.py
from dataclasses import dataclass
from django.utils import timezone
from .models import DomainCheck, EmailCheck

@dataclass
class DomainCheckResult:
    domain: str
    spf: str
    dkim: str
    dmarc: str
    risk_score: int
    risk_level: str
    last_checked: str

def check_domain(domain: str, user=None) -> DomainCheckResult:
    """
    Dummy deliverability check with hardcoded results for tests.
    """
    spf = "pass"
    dkim = "pass" if domain.endswith(".com") else "fail"
    dmarc = "fail" if "example.com" in domain else "pass"

    if domain == "example.com":
        risk_score = 7
        risk_level = "high"
    else:
        risk_score = 4
        risk_level = "medium"

    now = timezone.now()

    if user:
        DomainCheck.objects.update_or_create(
            domain=domain,
            user=user,
            defaults={
                "spf": spf,
                "dkim": dkim,
                "dmarc": dmarc,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "last_checked": now,
            },
        )

    return DomainCheckResult(
        domain=domain,
        spf=spf,
        dkim=dkim,
        dmarc=dmarc,
        risk_score=risk_score,
        risk_level=risk_level,
        last_checked=now.isoformat(),
    )


@dataclass
class EmailCheckResult:
    email: str
    status: str
    domain_type: str

def validate_email_smtp(email: str, user=None) -> EmailCheckResult:
    """
    Dummy SMTP/email validation for testing.
    """
    status = "valid" if "@" in email else "invalid"
    domain_type = "free" if email.endswith("@example.com") else "premium"

    if user:
        EmailCheck.objects.update_or_create(
            email=email,
            user=user,
            defaults={
                "status": status,
                "domain_type": domain_type,
            },
        )

    return EmailCheckResult(email=email, status=status, domain_type=domain_type)
