"""
Management command to extract text from invoice documents using OCR.

Usage:
    python manage.py extract_text --invoice-id 1
    python manage.py extract_text --all
    python manage.py extract_text --invoice-id 1 --force  # Re-extract even if text exists
"""

import logging
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from PIL import Image
import pytesseract

from claims.models import Invoice


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Extract text from invoice documents using OCR (Tesseract)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--invoice-uuid",
            type=uuid.UUID,
            help="Extract text from a specific invoice by UUID",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Extract text from all invoices that don't have extracted text yet",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-extract text even if it already exists",
        )
        parser.add_argument(
            "--lang",
            type=str,
            default="eng",
            help="OCR language code (default: eng). Use '+' for multiple languages, e.g., 'eng+spa'",
        )

    def handle(self, *args, **options):
        invoice_uuid = options.get("invoice_uuid")
        process_all = options.get("all")
        force = options.get("force")
        lang = options.get("lang")

        if not invoice_uuid and not process_all:
            raise CommandError("You must specify either --invoice-id or --all")

        if invoice_uuid:
            try:
                invoice = Invoice.objects.get(uuid=invoice_uuid)
            except Invoice.DoesNotExist:
                raise CommandError(f"Invoice with ID {invoice_uuid} does not exist")

            if invoice.extracted_text and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f"Invoice {invoice_uuid} already has extracted text. Use --force to re-extract."
                    )
                )
                return

            self.extract_text_from_invoice(invoice, lang)
        else:
            # Process all invoices without extracted text
            invoices = Invoice.objects.filter(document__isnull=False)
            if not force:
                invoices = invoices.filter(extracted_text="")

            total = invoices.count()
            self.stdout.write(f"Processing {total} invoice(s)...")

            success_count = 0
            error_count = 0

            for invoice in invoices:
                try:
                    self.extract_text_from_invoice(invoice, lang)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"Failed to extract text from invoice {invoice.id}: {e}",
                        exc_info=True,
                    )
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing invoice {invoice.id}: {e}"
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Completed: {success_count} succeeded, {error_count} failed"
                )
            )

    def extract_text_from_invoice(self, invoice, lang="eng"):
        """Extract text from an invoice document using OCR."""
        if not invoice.document:
            raise ValueError(f"Invoice {invoice.id} has no document attached")

        self.stdout.write(f"Processing invoice {invoice.id}...")

        # Get the document file path/URL
        document_path = invoice.document.name

        # Handle both local filesystem and S3 storage
        if default_storage.exists(document_path):
            # For local storage, we can open directly
            # For S3, we need to download temporarily
            try:
                # Try to open as local file first
                full_path = default_storage.path(document_path)
                image = Image.open(full_path)
            except (NotImplementedError, AttributeError):
                # Likely S3 storage - download to temp file
                import tempfile

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=Path(document_path).suffix
                ) as tmp_file:
                    with default_storage.open(document_path, "rb") as source_file:
                        tmp_file.write(source_file.read())
                    tmp_path = tmp_file.name

                try:
                    image = Image.open(tmp_path)
                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)
        else:
            raise FileNotFoundError(f"Document not found: {document_path}")

        # Convert to RGB if necessary (Tesseract requires RGB)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Extract text using Tesseract OCR
        try:
            extracted_text = pytesseract.image_to_string(image, lang=lang)
        except Exception as e:
            raise RuntimeError(f"OCR extraction failed: {e}")

        # Save extracted text to invoice
        invoice.extracted_text = extracted_text.strip()
        invoice.save(update_fields=["extracted_text"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully extracted {len(invoice.extracted_text)} characters from invoice {invoice.id}"
            )
        )

