import re
import unicodedata

from app.models.document import (
    ExtractedField,
    ExtractedLineItems,
    FieldStatus,
    InvoiceLineItem,
)


def _normalize_label(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.lower().split())


def _field(value: str) -> ExtractedField:
    if value.strip() in {"", "-", "—"}:
        return ExtractedField(
            value=None,
            status=FieldStatus.MISSING,
        )

    return ExtractedField(
        value=value.strip(),
        status=FieldStatus.FOUND,
    )


def _unit_price_field(value: str) -> ExtractedField:
    field = _field(value)

    if field.value is None:
        return field

    price_pattern = (
        r"-?(?:\d{1,3}(?:\.\d{3})+|\d+)"
        r"(?:[.,]\d+)?"
        r"\s*(?:€|EUR)?"
        r"(?:\s*/\s*[^\d\s][^\s]*)?"
    )

    if re.fullmatch(price_pattern, field.value, re.IGNORECASE):
        return field

    return ExtractedField(
        value=field.value,
        status=FieldStatus.DOUBTFUL,
    )


def extract_invoice_lines(text: str) -> ExtractedLineItems:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    headers = [
        {"concepto", "descripcion"},
        {"cantidad"},
        {"precio", "precio unitario", "precio / calculo"},
        {"importe"},
    ]

    start = None

    for index in range(len(lines) - 3):
        if all(
            _normalize_label(lines[index + offset]) in aliases
            for offset, aliases in enumerate(headers)
        ):
            start = index + 4
            break

    if start is None:
        return ExtractedLineItems(
            value=None,
            status=FieldStatus.MISSING,
        )

    stop_labels = {
        "forma de pago",
        "base imponible",
        "subtotal",
        "total",
        "total factura",
    }

    amount_pattern = re.compile(
        r"(?P<number>-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})"
        r"\s*(?:€|EUR)?",
        re.IGNORECASE,
    )

    items: list[InvoiceLineItem] = []
    incomplete = False
    has_doubtful_fields = False
    index = start

    while index < len(lines):
        if _normalize_label(lines[index]) in stop_labels:
            break

        cells = lines[index:index + 4]

        if len(cells) != 4:
            incomplete = True
            break

        description, quantity, unit_price, amount = cells
        amount_match = amount_pattern.fullmatch(amount)

        if (
            not any(character.isalpha() for character in description)
            or any(
                _normalize_label(cell) in stop_labels
                for cell in cells
            )
        ):
            incomplete = True
            break

        normalized_amount = (
            amount_match.group("number")
            .replace(".", "")
            .replace(",", ".")
        ) if amount_match else amount

        amount_field = _field(normalized_amount)
        if amount_field.value is not None and amount_match is None:
            amount_field.status = FieldStatus.DOUBTFUL
        if amount_field.status == FieldStatus.MISSING:
            incomplete = True

        items.append(
            InvoiceLineItem(
                description=_field(description),
                quantity=_field(quantity),
                unit_price=_unit_price_field(unit_price),
                amount=amount_field,
            )
        )

        index += 4

        has_doubtful_fields = any(
            field.status == FieldStatus.DOUBTFUL
            for item in items
            for field in (
                item.description,
                item.quantity,
                item.unit_price,
                item.amount,
            )
        )

    return ExtractedLineItems(
        value=items or None,
        status=(
            FieldStatus.DOUBTFUL
            if incomplete or has_doubtful_fields
            else FieldStatus.FOUND
            if items
            else FieldStatus.MISSING
        ),
    )
