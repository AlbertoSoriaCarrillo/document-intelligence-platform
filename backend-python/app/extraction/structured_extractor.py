from app.extraction.dni_extractor import extract_dni_fields
from app.models.document import (
    DocumentType,
    ExtractedField,
)


def extract_structured_fields(
    document_type: DocumentType,
    text: str,
) -> dict[str, ExtractedField]:
    if document_type == DocumentType.DNI:
        return extract_dni_fields(text)

    return {}