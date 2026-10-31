import re
from datetime import datetime

from app.core.messages import get_message
from app.extraction.errors import DocumentProcessingError
from app.extraction.invoice_line_extractor import extract_invoice_lines
from app.extraction.text_utils import normalize_label
from app.models.document import (
    ExtractedField,
    ExtractedLineItems,
    FieldStatus,
    InvoiceFields,
)


ISSUE_DATE_PATTERN = r"fecha de emisi[\u00f3o]n\s*:?\s*(\d{2}/\d{2}/\d{4})"

DATE_FORMAT = "%d/%m/%Y"

TAX_ID_PATTERN = (
    r"(?<![A-Z0-9])"
    r"(?:[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]|\d{8}[A-Z]|[XYZ]\d{7}[A-Z])"
    r"(?![A-Z0-9])"
)

AMOUNT_PATTERN = r"(?:\d{1,3}(?:\.\d{3})+|\d+)[,.]\d{2}"

INVOICE_NUMBER_PATTERN = (
    r"\bfactura(?:[ \t]+(?:n[\u00fau]mero|n[\u00bao\u00b0.]))?"
    r"[ \t]*[:#-]?[ \t]*"
    r"([A-Z0-9][A-Z0-9./-]*)(?=[ \t\r\n]|$)"
)

REQUIRED_STRUCTURE_PATTERNS = (
    r"\bfactura\b",
    r"detalle de la factura",
    r"\bemisor\b",
    r"\breceptor\b",
    r"concepto cantidad precio / calculo importe",
)

PARTY_HEADINGS = (
    ("issuer_tax_id", r"emisor"),
    ("recipient_tax_id", r"receptor(?: / cliente)?"),
)

PARTY_BLOCK_END_PATTERN = (
    r"(?=\b(?:EMISOR|RECEPTOR|TU SUMINISTRO|DETALLE DE LA FACTURA)\b|$)"
)

AMOUNT_FIELDS = (
    ("subtotal", r"base imponible"),
    ("tax", r"IVA(?:\s*\([^)]*\))?"),
    ("total", r"total factura"),
)

CURRENCY_PATTERN = r"\u20ac|\bEUR\b"


def _candidates(values: list[str]) -> ExtractedField:
    """Deduplica candidatos: uno es encontrado, varios dudosos y ninguno ausente.

    No elige arbitrariamente entre valores contradictorios ni valida su autenticidad.
    """
    values = list(dict.fromkeys(values))
    status = (
        FieldStatus.FOUND
        if len(values) == 1
        else FieldStatus.DOUBTFUL
        if values
        else FieldStatus.MISSING
    )
    return ExtractedField(value=" | ".join(values) or None, status=status)


def _amount(value: str) -> str:
    """Normaliza separadores de un importe ya reconocido, sin efectuar cálculos."""
    return value.replace(".", "").replace(",", ".") if "," in value else value


def ensure_compatible_invoice(text: str) -> None:
    """Comprueba los encabezados de la estructura admitida, no los valores.

    Raises:
        DocumentProcessingError: si faltan los marcadores estructurales requeridos.
    """
    # Los encabezados permiten variar los datos sin depender del nombre del proveedor.
    normalized = normalize_label(text)

    if not all(
        re.search(pattern, normalized)
        for pattern in REQUIRED_STRUCTURE_PATTERNS
    ):
        raise DocumentProcessingError(get_message("unsupported_structure"))


def extract_invoice_fields(text: str) -> InvoiceFields:
    """Extrae campos y conceptos desde texto con saltos de línea conservados.

    La ruta comprueba previamente la compatibilidad de la estructura. Los campos
    ausentes o contradictorios conservan su estado; no se validan controles
    fiscales ni sumas. Las fechas reconocidas sí se comprueban como fechas reales.
    """

    fields: dict[str, ExtractedField | ExtractedLineItems] = {}

    # No se atraviesan saltos de línea al buscar el número; exigir un dígito
    # evita interpretar encabezados como «Fecha» como números de factura.

    numbers = re.findall(INVOICE_NUMBER_PATTERN, text, re.I)

    fields["invoice_number"] = _candidates(
        [n.upper() for n in numbers if any(c.isdigit() for c in n)]
    )

    dates = re.findall(ISSUE_DATE_PATTERN, text, re.I)

    fields["issue_date"] = _candidates(dates)

    for date in dates:
        try:
            datetime.strptime(date, DATE_FORMAT)
        except ValueError:
            fields["issue_date"].status = FieldStatus.DOUBTFUL

    # Delimitar cada bloque evita atribuir al emisor el NIF del receptor
    # cuando el primero está ausente.

    for role, heading in PARTY_HEADINGS:
        blocks = re.findall(
            rf"\b{heading}\b(.*?)" + PARTY_BLOCK_END_PATTERN,
            text,
            re.I | re.S,
        )
        fields[role] = _candidates([
            match.upper()
            for block in blocks
            for match in re.findall(TAX_ID_PATTERN, block, re.I)
        ])

    for name, label in AMOUNT_FIELDS:
        values = re.findall(
            rf"\b{label}[ \t]*:?\s*({AMOUNT_PATTERN})(?![\d.,])",
            text,
            re.I,
        )
        fields[name] = _candidates([_amount(value) for value in values])

    fields["currency"] = _candidates(
        ["EUR"] if re.search(CURRENCY_PATTERN, text, re.I) else []
    )

    fields["line_items"] = extract_invoice_lines(text)

    return InvoiceFields(**fields)
