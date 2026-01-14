# deliverability/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .services import check_domain, validate_email_smtp
from .models import DomainCheck, EmailCheck

# -------------------
# Domain Deliverability
# -------------------
class DomainCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        domain = request.data.get("domain")
        if not domain:
            return Response({"error": "Domain is required."}, status=status.HTTP_400_BAD_REQUEST)

        result = check_domain(domain=domain, user=request.user)

        return Response(
            {
                "domain": result.domain,
                "spf": result.spf,
                "dkim": result.dkim,
                "dmarc": result.dmarc,
                "risk_score": result.risk_score,
                "risk_level": result.risk_level,
                "last_checked": result.last_checked,
            },
            status=status.HTTP_200_OK
        )

class DomainCheckListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        checks = DomainCheck.objects.filter(user=request.user).order_by("-last_checked")
        data = [
            {
                "domain": c.domain,
                "spf": c.spf,
                "dkim": c.dkim,
                "dmarc": c.dmarc,
                "risk_score": c.risk_score,
                "risk_level": c.risk_level,
                "last_checked": c.last_checked.isoformat(),
            }
            for c in checks
        ]
        return Response(data, status=status.HTTP_200_OK)

# -------------------
# Email Deliverability
# -------------------
class EmailCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        result = validate_email_smtp(email=email, user=request.user)

        return Response(
            {
                "email": result.email,
                "status": result.status,
                "domain_type": result.domain_type,
            },
            status=status.HTTP_201_CREATED
        )

class EmailBulkCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        emails = request.data.get("emails")
        if not emails or not isinstance(emails, list):
            return Response({"error": "A list of emails is required."}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for email in emails:
            result = validate_email_smtp(email=email, user=request.user)
            results.append({
                "email": result.email,
                "status": result.status,
                "domain_type": result.domain_type,
            })

        return Response({"results": results}, status=status.HTTP_201_CREATED)
