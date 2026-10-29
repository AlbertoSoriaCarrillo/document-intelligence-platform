import re
from decimal import Decimal, InvalidOperation

from app.models.document import ExtractedField, FieldStatus


DATE_PATTERN = r"\b\d{2}(?:[./-])\d{2}(?:[./-])\d{4}\b"

AMOUNT_PATTERN = (
    r"\d{1,3}(?:\.\d{3})*,\d{2}"
    r"|\d+(?:[.,]\d{2})"
)

TAX_ID_PATTERN = (
    r"(?<![A-Z0-9])"
    r"(?:"
    r"[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]"
    r"|\d{8}[A-Z]"
    r"|[XYZ]\d{7}[A-Z]"
    r")"
    r"(?![A-Z0-9])"
)


def _found(value: str) -> ExtractedField:
    return ExtractedField(
        value=value,
        status=FieldStatus.FOUND,
    )


def _missing() -> ExtractedField:
    return ExtractedField(
        value=None,
        status=FieldStatus.MISSING,
    )


def _doubtful(value: str) -> ExtractedField:
    return ExtractedField(
        value=value,
        status=FieldStatus.DOUBTFUL,
    )


def _normalize_amount(value: str) -> str:
    cleaned = value.replace(" ", "").replace("€", "")

    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        return f"{Decimal(cleaned):.2f}"
    except InvalidOperation:
        return value


def _find_amount(
    text: str,
    labels: str,
) -> str | None:
    match = re.search(
        rf"(?:{labels}).{{0,15}}?({AMOUNT_PATTERN})",
        text,
        re.IGNORECASE,
    )

    return (
        _normalize_amount(match.group(1))
        if match
        else None
    )


def _find_corrected_company_tax_ids(text: str) -> list[str]:
    """Recupera candidatos de empresa junto a CIF/NIF."""
    matches = re.finditer(
        r"\b(?:CIF|NIF)\s*[:.-]?\s*"
        r"([ABCDEFGHJNPQRSUVW])([0-9O]{7})([0-9A-JO])"
        r"(?![A-Z0-9])",
        text,
        re.IGNORECASE,
    )

    candidates: list[str] = []

    for match in matches:
        prefix, digits, control = (
            part.upper() for part in match.groups()
        )

        if "O" not in digits and control != "O":
            continue

        candidate = (
            prefix
            + digits.replace("O", "0")
            + ("0" if control == "O" else control)
        )

        if candidate not in candidates:
            candidates.append(candidate)

    return candidates


def extract_invoice_fields(
    text: str,
) -> dict[str, ExtractedField]:
    normalized = re.sub(r"\s+", " ", text).strip()

    invoice_number_match = re.search(
        r"(?:n[úu]mero de factura|"
        r"factura\s*(?:n[ºo°.]|n[úu]mero)?)"
        r"[\s:#-]*"
        r"([A-Z0-9][A-Z0-9./-]{2,})",
        normalized,
        re.IGNORECASE,
    )

    issue_date_match = re.search(
        rf"(?:fecha de emisi[oó]n|fecha factura|fecha)"
        rf".{{0,15}}?({DATE_PATTERN})",
        normalized,
        re.IGNORECASE,
    )

    issuer_tax_match = re.search(
        rf"(?:emisor|proveedor).{{0,50}}?"
        rf"({TAX_ID_PATTERN})",
        normalized,
        re.IGNORECASE,
    )

    recipient_tax_match = re.search(
        rf"(?:receptor|cliente).{{0,50}}?"
        rf"({TAX_ID_PATTERN})",
        normalized,
        re.IGNORECASE,
    )

    detected_tax_ids = list(
        dict.fromkeys(
            match.upper()
            for match in re.findall(
                TAX_ID_PATTERN,
                normalized,
                re.IGNORECASE,
            )
        )
    )

    for candidate in _find_corrected_company_tax_ids(normalized):
        if candidate not in detected_tax_ids:
            detected_tax_ids.append(candidate)

    subtotal = _find_amount(
        normalized,
        r"base imponible|subtotal",
    )

    tax = _find_amount(
        normalized,
        r"\biva\b|impuestos?",
    )

    total = _find_amount(
        normalized,
        r"importe total|total factura|\btotal\b",
    )

    currency_match = re.search(
        r"€|\bEUR\b",
        normalized,
        re.IGNORECASE,
    )

    return {
        "invoice_number": (
            _found(invoice_number_match.group(1).upper())
            if invoice_number_match
            else _missing()
        ),
        "issue_date": (
            _found(issue_date_match.group(1))
            if issue_date_match
            else _missing()
        ),
        "issuer_tax_id": (
            _found(issuer_tax_match.group(1).upper())
            if issuer_tax_match
            else _missing()
        ),
        "recipient_tax_id": (
            _found(recipient_tax_match.group(1).upper())
            if recipient_tax_match
            else _missing()
        ),
        "subtotal": (
            _found(subtotal)
            if subtotal
            else _missing()
        ),
        "tax": (
            _found(tax)
            if tax
            else _missing()
        ),
        "total": (
            _found(total)
            if total
            else _missing()
        ),
        "currency": (
            _found("EUR")
            if currency_match
            else _missing()
        ),
        "detected_tax_ids": (
            _doubtful(", ".join(detected_tax_ids))
            if detected_tax_ids
            else _missing()
        ),
        "line_items": _missing(),
    }