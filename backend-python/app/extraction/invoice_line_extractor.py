import re
import unicodedata

from app.models.document import (
    ExtractedField,
    ExtractedLineItems,
    FieldStatus,
    InvoiceLineItem,
)
from app.extraction.ocr_layout import OcrWord
from app.extraction.ocr_layout import (
    OcrWord,
    group_words_into_rows,
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
            or amount_match is None
        ):
            incomplete = True
            break

        normalized_amount = (
            amount_match.group("number")
            .replace(".", "")
            .replace(",", ".")
        )

        items.append(
            InvoiceLineItem(
                description=_field(description),
                quantity=_field(quantity),
                unit_price=_unit_price_field(unit_price),
                amount=_field(normalized_amount),
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


def find_table_header(
    rows: list[list[OcrWord]],
) -> tuple[int, dict[str, OcrWord]] | None:
    aliases = {
        "concepto": "description",
        "descripcion": "description",
        "cantidad": "quantity",
        "unidades": "quantity",
        "precio": "unit_price",
        "importe": "amount",
    }

    required_columns = {
        "description",
        "quantity",
        "unit_price",
        "amount",
    }

    for index, row in enumerate(rows):
        columns: dict[str, OcrWord] = {}
        ambiguous = False

        for word in row:
            label = _normalize_label(word.text).strip(":.")
            column = aliases.get(label)

            if column is None:
                continue

            if column in columns:
                ambiguous = True
                break

            columns[column] = word

        if not ambiguous and set(columns) == required_columns:
            return index, columns

    return None


def split_row_into_cells(
    row: list[OcrWord],
    columns: dict[str, OcrWord],
) -> dict[str, str] | None:
    ordered_columns = sorted(
        columns.items(),
        key=lambda item: item[1].left,
    )

    if not ordered_columns:
        return None

    boundaries: list[float] = []

    for index in range(len(ordered_columns) - 1):
        current_header = ordered_columns[index][1]
        next_header = ordered_columns[index + 1][1]

        if current_header.right >= next_header.left:
            return None

        boundary = (
            current_header.right + next_header.left
        ) / 2

        boundaries.append(boundary)

    cells: dict[str, list[str]] = {
        name: []
        for name, _ in ordered_columns
    }

    for word in sorted(row, key=lambda item: item.left):
        # Si una palabra cruza una separación, no adivinamos.
        if any(
            word.left < boundary < word.right
            for boundary in boundaries
        ):
            return None

        center = (word.left + word.right) / 2

        column_index = sum(
            center > boundary
            for boundary in boundaries
        )

        column_name = ordered_columns[column_index][0]
        cells[column_name].append(word.text)

    return {
        name: " ".join(parts)
        for name, parts in cells.items()
    }


def extract_invoice_lines_from_ocr(
    regions: list[list[OcrWord]],
) -> ExtractedLineItems:
    items: list[InvoiceLineItem] = []
    doubtful = False

    amount_pattern = re.compile(
        r"(?P<number>-?(?:\d{1,3}(?:\.\d{3})+|\d+),\d{2})"
        r"\s*(?:€|EUR)?",
        re.IGNORECASE,
    )

    stop_pattern = re.compile(
        r"\b(?:forma de pago|base imponible|subtotal|total factura)\b"
        r"|^total\b"
    )

    for region in regions:
        rows = group_words_into_rows(region)
        header = find_table_header(rows)

        if header is None:
            continue

        header_index, columns = header

        for row in rows[header_index + 1:]:
            row_text = " ".join(word.text for word in row)

            if stop_pattern.search(_normalize_label(row_text)):
                break

            cells = split_row_into_cells(row, columns)

            if cells is None:
                doubtful = True
                break

            description = cells["description"]

            if (
                not any(character.isalpha() for character in description)
                or not any(
                    cells[name]
                    for name in ("quantity", "unit_price", "amount")
                )
            ):
                doubtful = True
                break

            amount = _field(cells["amount"])

            if amount.value is not None:
                match = amount_pattern.fullmatch(amount.value)

                if match:
                    amount.value = (
                        match.group("number")
                        .replace(".", "")
                        .replace(",", ".")
                    )
                else:
                    amount.status = FieldStatus.DOUBTFUL

            item = InvoiceLineItem(
                description=_field(description),
                quantity=_field(cells["quantity"]),
                unit_price=_unit_price_field(cells["unit_price"]),
                amount=amount,
            )

            fields = [
                item.description,
                item.quantity,
                item.unit_price,
                item.amount,
            ]

            # Una fila con palabras poco fiables requiere revisión.
            if any(word.confidence < 80 for word in row):
                for field in fields:
                    if field.status == FieldStatus.FOUND:
                        field.status = FieldStatus.DOUBTFUL

            if (
                amount.status == FieldStatus.MISSING
                or any(
                    field.status == FieldStatus.DOUBTFUL
                    for field in fields
                )
            ):
                doubtful = True

            items.append(item)

    return ExtractedLineItems(
        value=items or None,
        status=(
            FieldStatus.DOUBTFUL
            if doubtful
            else FieldStatus.FOUND
            if items
            else FieldStatus.MISSING
        ),
    )