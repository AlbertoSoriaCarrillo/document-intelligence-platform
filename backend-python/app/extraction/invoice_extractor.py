import re
from decimal import Decimal, InvalidOperation

from app.models.document import ExtractedField, FieldStatus
from app.extraction.ocr_layout import OcrWord


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



def _party_fields_from_layout(
    regions: list[list[OcrWord]],
) -> dict[str, ExtractedField]:
    """Associate IDs with nearby role headings within each independent image.

    Distances are normalized image coordinates, not fixed template positions.
    Ambiguous assignments and conflicting IDs are deliberately left missing.
    FOUND means extracted, not that the tax ID checksum has been validated.
    """
    labels = {
        "EMISOR": "issuer_tax_id", "PROVEEDOR": "issuer_tax_id",
        "RECEPTOR": "recipient_tax_id", "CLIENTE": "recipient_tax_id",
    }
    matches: dict[str, dict[str, ExtractedField]] = {
        "issuer_tax_id": {}, "recipient_tax_id": {},
    }
    for words in regions:
        anchors = [
            (word, labels[word.text.upper().strip(" :.,/()")])
            for word in words
            if word.confidence >= 60
            and word.text.upper().strip(" :.,/()") in labels
        ]
        for word in words:
            if word.confidence < 35:
                continue
            raw = word.text.upper().strip(" :.,;()")
            value = raw if re.fullmatch(TAX_ID_PATTERN, raw) else None
            corrected = False
            if value is None:
                # Only repair a company ID next to an explicit CIF/NIF label.
                has_label = any(
                    other.text.upper().strip(" :.") in {"CIF", "NIF"}
                    and other.confidence >= 60
                    and 0 <= word.left - other.right <= 0.06
                    and min(word.bottom, other.bottom) > max(word.top, other.top)
                    for other in words
                )
                candidates = _find_corrected_company_tax_ids("CIF " + raw) if has_label else []
                if not candidates:
                    continue
                value = candidates[0]
                corrected = True

            scores: dict[str, float] = {}
            for anchor, role in anchors:
                vertical_gap = word.top - anchor.bottom
                horizontal_gap = abs(word.left - anchor.left)
                below = 0 <= vertical_gap <= 0.18 and horizontal_gap <= 0.18
                inline = (
                    min(word.bottom, anchor.bottom) > max(word.top, anchor.top)
                    and 0 <= word.left - anchor.right <= 0.12
                )
                if not (below or inline):
                    continue
                score = 2 * horizontal_gap + max(vertical_gap, 0)
                scores[role] = min(scores.get(role, float("inf")), score)
            ranked = sorted(scores, key=scores.get)
            if not ranked:
                continue
            if len(ranked) > 1 and scores[ranked[1]] - scores[ranked[0]] < 0.04:
                continue
            role = ranked[0]
            field = _doubtful(value) if corrected or word.confidence < 80 else _found(value)
            previous = matches[role].get(value)
            if previous is None or field.status == FieldStatus.DOUBTFUL:
                matches[role][value] = field

    result = {
        role: next(iter(values.values())) if len(values) == 1 else _missing()
        for role, values in matches.items()
    }
    # An ID assigned to both parties is not sufficient evidence to choose.
    if result["issuer_tax_id"].value and result["issuer_tax_id"].value == result["recipient_tax_id"].value:
        return {role: _missing() for role in result}
    return result


def extract_invoice_fields(
    text: str,
    ocr_regions: list[list[OcrWord]] | None = None,
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

    fields = {
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
    if ocr_regions:
        fields.update(_party_fields_from_layout(ocr_regions))
    return fields