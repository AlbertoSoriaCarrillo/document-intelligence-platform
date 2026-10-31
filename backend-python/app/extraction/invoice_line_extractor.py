import re

from app.extraction.text_utils import normalize_label
from app.models.document import (
    ExtractedField,
    ExtractedLineItems,
    FieldStatus,
    InvoiceLineItem,
)


TABLE_HEADERS = (
    frozenset({"concepto", "descripcion"}),
    frozenset({"cantidad"}),
    frozenset({"precio", "precio unitario", "precio / calculo"}),
    frozenset({"importe"}),
)

# Los totales y el bloque de pago no son conceptos de la tabla.
TABLE_STOP_LABELS = frozenset({
    "forma de pago",
    "base imponible",
    "subtotal",
    "total",
    "total factura",
})

PRICE_PATTERN = (
    r"-?(?:\d{1,3}(?:\.\d{3})+|\d+)"
    r"(?:[.,]\d+)?"
    r"\s*(?:€|EUR)?"
    r"(?:\s*/\s*[^\d\s][^\s]*)?"
)

AMOUNT_PATTERN = re.compile(
    r"(?P<number>-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})"
    r"\s*(?:€|EUR)?",
    re.IGNORECASE,
)


def _field(value: str) -> ExtractedField:
    """Conserva el contenido de una celda; vacío o guion representa un dato ausente."""
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
    """Comprueba el formato del precio y conserva textos explicativos como dudosos.

    Admite unidades, pero no interpreta su significado ni verifica cálculos.
    """
    field = _field(value)

    if field.value is None:
        return field

    if re.fullmatch(PRICE_PATTERN, field.value, re.IGNORECASE):
        return field

    return ExtractedField(
        value=field.value,
        status=FieldStatus.DOUBTFUL,
    )


def extract_invoice_lines(text: str) -> ExtractedLineItems:
    """Lee la tabla en el orden de texto de la muestra: cuatro celdas por concepto.

    Devuelve los conceptos reconocidos y un estado global. Si se pierde la
    estructura, conserva lo leído como dudoso en lugar de reconstruir filas
    arbitrarias. No admite descripciones que ocupen varias celdas de texto.
    """
    # Los saltos separan celdas; colapsarlos mezclaría conceptos con cantidades.
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    start = None

    for index in range(len(lines) - 3):
        if all(
            normalize_label(lines[index + offset]) in aliases
            for offset, aliases in enumerate(TABLE_HEADERS)
        ):
            start = index + 4
            break

    if start is None:
        return ExtractedLineItems(
            value=None,
            status=FieldStatus.MISSING,
        )

    items: list[InvoiceLineItem] = []
    incomplete = False
    index = start

    while index < len(lines):
        if normalize_label(lines[index]) in TABLE_STOP_LABELS:
            break

        cells = lines[index:index + 4]

        if len(cells) != 4:
            incomplete = True
            break

        description, quantity, unit_price, amount = cells
        amount_match = AMOUNT_PATTERN.fullmatch(amount)

        if (
            not any(character.isalpha() for character in description)
            or any(
                normalize_label(cell) in TABLE_STOP_LABELS
                for cell in cells
            )
        ):
            incomplete = True
            break

        # Normalizar el importe reconocido para conservar la precisión decimal.
        normalized_amount = (
            amount_match.group("number")
            .replace(".", "")
            .replace(",", ".")
        ) if amount_match else amount

        # No se calcula un importe ausente: se conserva la incertidumbre del documento.
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

    # Una cantidad ausente puede ser legítima; los datos dudosos sí
    # requieren revisión del conjunto de conceptos.
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