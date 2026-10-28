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


class DocumentClassification(BaseModel):
    document_type: DocumentType
    status: ClassificationStatus
    score: int
    evidence: list[str]


class DocumentInspectionResponse(BaseModel):
    filename: str
    content_type: str
    size: int
    character_count: int
    extraction_method: str
    classification: DocumentClassification
    text_preview: str
    warnings: list[str]