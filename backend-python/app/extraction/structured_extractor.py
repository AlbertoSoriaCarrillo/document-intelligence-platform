from app.extraction.dni_extractor import extract_dni_fields
from app.models.document import (
    DocumentType,
    ExtractedField,
)
from app.extraction.invoice_extractor import extract_invoice_fields


def extract_structured_fields(
    document_type: DocumentType,
    text: str,
) -> dict[str, ExtractedField]:
    if document_type == DocumentType.DNI:
        return extract_dni_fields(text)

    if document_type == DocumentType.INVOICE:
       return extract_invoice_fields(text)
    
    return {}