from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Claim, Invoice


User = get_user_model()


@csrf_exempt  # For API/mobile clients; adjust if using CSRF tokens
@require_POST
@transaction.atomic
def create_claim(request):
    """
    Create a new claim and attach uploaded invoice files.

    Expected request (multipart/form-data):
      - files: one or many under the key "invoices"

    Authentication:
      - Uses the authenticated user as `pet_parent`.
    """

    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Authentication required."}, status=401)

    invoice_files = request.FILES.getlist("invoices")

    if not invoice_files:
        return JsonResponse(
            {"detail": "At least one invoice file must be uploaded under 'invoices'."},
            status=400,
        )

    claim = Claim.objects.create(pet_parent=request.user)

    created_invoices = []
    for f in invoice_files:
        invoice = Invoice.objects.create(
            claim=claim,
            document=f,
        )
        created_invoices.append(
            {
                "id": invoice.id,
                "document": invoice.document.name,
            }
        )

    return JsonResponse(
        {
            "id": claim.id,
            "pet_parent_id": claim.pet_parent_id,
            "invoices": created_invoices,
        },
        status=201,
    )
