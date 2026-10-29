from app.extraction.ocr_layout import (
    OcrWord,
    group_words_into_rows,
)
from app.extraction.invoice_line_extractor import find_table_header
from app.extraction.invoice_line_extractor import split_row_into_cells
from app.extraction.invoice_line_extractor import (
    extract_invoice_lines_from_ocr,
)
from app.models.document import FieldStatus


def word(text, left, top, confidence=95):
    return OcrWord(
        text=text,
        confidence=confidence,
        left=left,
        top=top,
        right=left + 0.08,
        bottom=top + 0.02,
        block=1,
        paragraph=1,
        line=1,
    )


def test_groups_and_orders_words_geometrically():
    words = [
        word("10,00", 0.8, 0.303),
        word("Importe", 0.8, 0.202),
        word("Servicio", 0.1, 0.3),
        word("Concepto", 0.1, 0.2),
    ]

    rows = group_words_into_rows(words)

    assert [
        [item.text for item in row]
        for row in rows
    ] == [
        ["Concepto", "Importe"],
        ["Servicio", "10,00"],
    ]


def test_ignores_low_confidence_noise():
    rows = group_words_into_rows([
        word("Servicio", 0.1, 0.3),
        word("???", 0.5, 0.3, confidence=10),
    ])

    assert len(rows) == 1
    assert [item.text for item in rows[0]] == ["Servicio"]


def test_returns_empty_rows_without_words():
    assert group_words_into_rows([]) == []


def test_finds_headers_with_columns_in_another_order():
    rows = group_words_into_rows([
        word("Importe", 0.1, 0.2),
        word("Descripción", 0.3, 0.2),
        word("Precio", 0.6, 0.2),
        word("Cantidad", 0.8, 0.2),
    ])

    result = find_table_header(rows)

    assert result is not None
    index, columns = result

    assert index == 0
    assert columns["description"].left == 0.3
    assert columns["quantity"].left == 0.8
    assert columns["unit_price"].left == 0.6
    assert columns["amount"].left == 0.1


def test_rejects_incomplete_headers():
    rows = group_words_into_rows([
        word("Concepto", 0.1, 0.2),
        word("Importe", 0.8, 0.2),
    ])

    assert find_table_header(rows) is None


def test_assigns_words_to_cells():
    columns = {
        "description": word("Concepto", 0.1, 0.2),
        "quantity": word("Cantidad", 0.4, 0.2),
        "unit_price": word("Precio", 0.6, 0.2),
        "amount": word("Importe", 0.8, 0.2),
    }

    row = [
        word("10,00", 0.8, 0.3),
        word("Servicio", 0.1, 0.3),
        word("5,00", 0.6, 0.3),
        word("2", 0.4, 0.3),
    ]

    assert split_row_into_cells(row, columns) == {
        "description": "Servicio",
        "quantity": "2",
        "unit_price": "5,00",
        "amount": "10,00",
    }


def test_rejects_word_crossing_column_boundary():
    columns = {
        "description": word("Concepto", 0.1, 0.2),
        "amount": word("Importe", 0.5, 0.2),
    }

    # La separación está en 0.34.
    # Esta palabra ocupa de 0.31 a 0.39.
    row = [word("Ambigua", 0.31, 0.3)]

    assert split_row_into_cells(row, columns) is None


def test_ocr_preserves_line_with_missing_amount():
    region = [
        word("Concepto", 0.1, 0.2),
        word("Cantidad", 0.4, 0.2),
        word("Precio", 0.6, 0.2),
        word("Importe", 0.8, 0.2),
        word("Servicio", 0.1, 0.3),
        word("1", 0.4, 0.3),
        word("3,50", 0.6, 0.3),
        word("Subtotal", 0.1, 0.4),
        word("3,50", 0.8, 0.4),
    ]

    result = extract_invoice_lines_from_ocr([region])

    assert result.value is not None
    assert len(result.value) == 1
    assert result.value[0].description.value == "Servicio"
    assert result.value[0].amount.value is None
    assert result.value[0].amount.status == FieldStatus.MISSING
    assert result.status == FieldStatus.DOUBTFUL