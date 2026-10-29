from enum import StrEnum
from pydantic import BaseModel


class DocumentType(StrEnum):
    DNI = "dni"
    INVOICE = "invoice"
    DELIVERY_NOTE = "delivery_note"
    RECEIPT = "receipt"
    UNKNOWN = "unknown"


class ClassificationStatus(StrEnum):
    CONFIDENT = "confident"
    DOUBTFUL = "doubtful"
    UNKNOWN = "unknown"


class FieldStatus(StrEnum):
    FOUND = "found"
    DOUBTFUL = "doubtful"
    MISSING = "missing"


class DocumentClassification(BaseModel):
    document_type: DocumentType
    status: ClassificationStatus
    score: int
    evidence: list[str]


class ExtractedField(BaseModel):
    value: str | None
    status: FieldStatus


class InvoiceLineItem(BaseModel):
    description: ExtractedField
    quantity: ExtractedField
    unit_price: ExtractedField
    amount: ExtractedField


class ExtractedLineItems(BaseModel):
    value: list[InvoiceLineItem] | None
    status: FieldStatus


class DocumentInspectionResponse(BaseModel):
    filename: str
    content_type: str
    size: int
    character_count: int
    extraction_method: str
    classification: DocumentClassification
    extracted_fields: dict[str, ExtractedField | ExtractedLineItems]
    text_preview: str
    warnings: list[str]