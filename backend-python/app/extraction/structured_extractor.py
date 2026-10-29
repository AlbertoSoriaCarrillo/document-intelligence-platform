from app.extraction.dni_extractor import extract_dni_fields
from app.extraction.ocr_layout import OcrWord
from app.models.document import (
    DocumentType,
    ExtractedField,
)
from app.extraction.invoice_extractor import extract_invoice_fields
from app.models.document import ExtractedLineItems


def extract_structured_fields(
    document_type: DocumentType,
    text: str,
    ocr_regions: list[list[OcrWord]] | None = None,
) -> dict[str, ExtractedField | ExtractedLineItems]:
    if document_type == DocumentType.DNI:
        return extract_dni_fields(text)

    if document_type == DocumentType.INVOICE:
        return extract_invoice_fields(text, ocr_regions)
    
    return {}