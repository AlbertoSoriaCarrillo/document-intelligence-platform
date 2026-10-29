from enum import StrEnum
from pydantic import BaseModel


class FieldStatus(StrEnum):
    FOUND = "found"
    DOUBTFUL = "doubtful"
    MISSING = "missing"


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
    extracted_fields: dict[str, ExtractedField | ExtractedLineItems]
    text_preview: str
    warnings: list[str]