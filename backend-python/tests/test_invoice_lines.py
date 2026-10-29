from app.extraction.invoice_line_extractor import extract_invoice_lines
from app.models.document import FieldStatus


def test_empty_table_is_missing():
    result = extract_invoice_lines("Concepto\nCantidad\nPrecio / cálculo\nImporte\nBase imponible\n0,00 EUR")
    assert result.value is None
    assert result.status == FieldStatus.MISSING


def test_ambiguous_amount_propagates_to_lines():
    result = extract_invoice_lines("Concepto\nCantidad\nPrecio / cálculo\nImporte\nServicio\n-\n5,00 EUR\nilegible")
    assert result.value[0].amount.status == FieldStatus.DOUBTFUL
    assert result.value[0].quantity.status == FieldStatus.MISSING
    assert result.status == FieldStatus.DOUBTFUL


def test_missing_amount_preserves_line():
    result = extract_invoice_lines("Concepto\nCantidad\nPrecio / cálculo\nImporte\nServicio\n1 mes\n5,00 EUR\n-")
    assert result.value[0].amount.status == FieldStatus.MISSING
    assert result.status == FieldStatus.DOUBTFUL


def test_extracts_lines_without_including_totals():
    text = """
Concepto
Cantidad
Precio / cálculo
Importe
Energía consumida
186 kWh
0,1675 €/kWh
31,16 €
Alquiler del contador
30 días
0,0270 €/día
0,81 €
Base imponible
31,97 EUR
"""
    result = extract_invoice_lines(text)

    assert result.status == FieldStatus.FOUND
    assert result.value is not None
    assert len(result.value) == 2
    assert result.value[0].description.value == "Energía consumida"
    assert result.value[0].quantity.value == "186 kWh"
    assert result.value[0].amount.value == "31.16"
    assert result.value[1].amount.value == "0.81"


def test_returns_missing_without_table_headers():
    result = extract_invoice_lines("Total factura: 63,27 EUR")

    assert result.value is None
    assert result.status == FieldStatus.MISSING


def test_marks_incomplete_table_as_doubtful():
    result = extract_invoice_lines(
        "Concepto\nCantidad\nPrecio\nImporte\nServicio\n1"
    )

    assert result.value is None
    assert result.status == FieldStatus.DOUBTFUL


def test_marks_explanatory_price_as_doubtful():
    text = """
Concepto
Cantidad
Precio / cálculo
Importe
Impuesto eléctrico
-
Cuota de ejemplo
2,33 €
"""
    result = extract_invoice_lines(text)

    assert result.value is not None
    item = result.value[0]
    assert item.quantity.status == FieldStatus.MISSING
    assert item.unit_price.value == "Cuota de ejemplo"
    assert item.unit_price.status == FieldStatus.DOUBTFUL
    assert item.amount.value == "2.33"
    assert result.status == FieldStatus.DOUBTFUL
