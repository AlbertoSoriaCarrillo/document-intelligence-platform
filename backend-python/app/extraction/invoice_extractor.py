import re
from datetime import datetime

from app.extraction.invoice_line_extractor import extract_invoice_lines, _normalize_label
from app.extraction.text_extractor import DocumentProcessingError
from app.models.document import ExtractedField, ExtractedLineItems, FieldStatus

TAX_ID_PATTERN = r"(?<![A-Z0-9])(?:[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]|\d{8}[A-Z]|[XYZ]\d{7}[A-Z])(?![A-Z0-9])"
AMOUNT_PATTERN = r"(?:\d{1,3}(?:\.\d{3})+|\d+)[,.]\d{2}"


def _candidates(values: list[str]) -> ExtractedField:
    values = list(dict.fromkeys(values))
    return ExtractedField(value=" | ".join(values) or None, status=(
        FieldStatus.FOUND if len(values) == 1 else FieldStatus.DOUBTFUL if values else FieldStatus.MISSING
    ))


def _amount(value: str) -> str:
    return value.replace(".", "").replace(",", ".") if "," in value else value


def ensure_compatible_invoice(text: str) -> None:
    # Structural anchors, independent of vendor name and individual field values.
    normalized = _normalize_label(text)
    if not (re.search(r"\bfactura\b", normalized)
            and "detalle de la factura" in normalized
            and re.search(r"\bemisor\b", normalized)
            and re.search(r"\breceptor\b", normalized)
            and "concepto cantidad precio / calculo importe" in normalized):
        raise DocumentProcessingError("Unsupported invoice structure; expected the Lumenia sample structure.")


def extract_invoice_fields(text: str) -> dict[str, ExtractedField | ExtractedLineItems]:
    fields = {}
    # Stop at headings, including when the number itself has been omitted.
    numbers = re.findall(
        r"\bfactura(?:[ \t]+(?:n[\u00fau]mero|n[\u00bao\u00b0.]))?[ \t]*[:#-]?[ \t]*"
        r"([A-Z0-9][A-Z0-9./-]*)(?=[ \t\r\n]|$)", text, re.I)
    fields["invoice_number"] = _candidates([n.upper() for n in numbers if any(c.isdigit() for c in n)])
    dates = re.findall(r"fecha de emisi[\u00f3o]n\s*:?\s*(\d{2}/\d{2}/\d{4})", text, re.I)
    fields["issue_date"] = _candidates(dates)
    for date in dates:
        try:
            datetime.strptime(date, "%d/%m/%Y")
        except ValueError:
            fields["issue_date"].status = FieldStatus.DOUBTFUL
    # Bound each party by the next structural heading, never by character distance.
    for role, heading in (("issuer_tax_id", "emisor"), ("recipient_tax_id", "receptor(?: / cliente)?")):
        blocks = re.findall(rf"\b{heading}\b(.*?)(?=\b(?:EMISOR|RECEPTOR|TU SUMINISTRO|DETALLE DE LA FACTURA)\b|$)", text, re.I | re.S)
        fields[role] = _candidates([m.upper() for block in blocks for m in re.findall(TAX_ID_PATTERN, block, re.I)])
    for name, label in (("subtotal", "base imponible"), ("tax", r"IVA(?:\s*\([^)]*\))?"), ("total", "total factura")):
        values = re.findall(rf"\b{label}[ \t]*:?\s*({AMOUNT_PATTERN})(?![\d.,])", text, re.I)
        fields[name] = _candidates([_amount(v) for v in values])
    fields["currency"] = _candidates(["EUR"] if re.search(r"\u20ac|\bEUR\b", text, re.I) else [])
    fields["line_items"] = extract_invoice_lines(text)
    return fields
