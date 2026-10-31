from enum import StrEnum
from pydantic import BaseModel


class FieldStatus(StrEnum):
    """Estado de extracción; FOUND no equivale a validación fiscal."""
    FOUND = "found"
    DOUBTFUL = "doubtful"
    MISSING = "missing"


class ExtractedField(BaseModel):
    """Valor textual o ausencia explícita, acompañado de su estado."""
    value: str | None
    status: FieldStatus


class InvoiceLineItem(BaseModel):
    """Concepto con estado por celda; cantidades y precios conservan sus unidades."""
    description: ExtractedField
    quantity: ExtractedField
    unit_price: ExtractedField
    amount: ExtractedField


class ExtractedLineItems(BaseModel):
    """Conceptos reconocidos y estado agregado de la extracción de la tabla."""
    value: list[InvoiceLineItem] | None
    status: FieldStatus


class InvoiceFields(BaseModel):
    """Campos explícitos de la factura, alineados con InvoiceFields de Angular."""

    invoice_number: ExtractedField
    issue_date: ExtractedField
    issuer_tax_id: ExtractedField
    recipient_tax_id: ExtractedField
    subtotal: ExtractedField
    tax: ExtractedField
    total: ExtractedField
    currency: ExtractedField
    line_items: ExtractedLineItems


class DocumentInspectionResponse(BaseModel):
    """Contrato HTTP compartido con los modelos TypeScript de la interfaz."""
    filename: str
    content_type: str
    size: int
    character_count: int
    extraction_method: str
    extracted_fields: InvoiceFields
    text_preview: str
    warnings: list[str]