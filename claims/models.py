from django.db import models

from common.models import BaseModel


class Clinic(BaseModel):
    """
    A veterinary clinic that issues invoices for services.

    Clinics can be reused across multiple invoices and claims.
    """

    name = models.CharField(max_length=255)
    tax_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="Tax identifier / registration number of the clinic, if available.",
    )
    # Additional clinic fields (address, contact info, etc.) can be added later


class Claim(BaseModel):
    """
    A single insurance claim initiated by a pet parent.

    One claim can have one or more invoices attached to it.
    Line‑level detail lives in `InvoiceLine` through the `Invoice` model.
    """

    pet_parent = models.ForeignKey(
        "auth.User",
        related_name="claims",
        on_delete=models.PROTECT,
    )

    # Additional high‑level claim fields (status, identifiers, etc.) can be
    # added later as the workflow is fleshed out.


class Invoice(BaseModel):
    """
    An invoice issued by a clinic for veterinary services.

    Each invoice belongs to exactly one claim, and has one or more line items.
    """

    claim = models.ForeignKey(
        Claim,
        related_name="invoices",
        on_delete=models.CASCADE,
    )

    clinic = models.ForeignKey(
        Clinic,
        related_name="invoices",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="The clinic that issued this invoice. May be null if clinic info is not yet extracted.",
    )
    document = models.FileField(
        upload_to="invoices/",
        null=True,
        blank=True,
        help_text=(
            "The scanned/screenshot document of the invoice. "
            "Uses local filesystem storage in development, S3 in production "
            "(configure via DEFAULT_FILE_STORAGE setting)."
        ),
    )
    invoice_number = models.CharField(max_length=64, blank=True)
    issued_at = models.DateField(null=True, blank=True)

    currency = models.CharField(max_length=8, default="EUR")
    subtotal_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )


class InvoiceLine(BaseModel):
    """
    A single line item within an invoice, e.g. consultation, X‑ray, medication.
    """

    invoice = models.ForeignKey(
        Invoice,
        related_name="line_items",
        on_delete=models.CASCADE,
    )

    description = models.TextField()
    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=1,
        help_text="Number of units for this line (e.g. 2 boxes of medication).",
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total amount for this line as shown (or implied) on the invoice.",
    )

    # Optional semantic fields that can be filled by the document-understanding pipeline
    category = models.CharField(
        max_length=128,
        blank=True,
        help_text="Internal category (e.g. consultation, imaging, surgery, medication).",
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tax rate applied to this line, if known (e.g. 21.00 for 21%).",
    )