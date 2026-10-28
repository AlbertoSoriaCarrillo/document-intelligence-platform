from app.extraction.invoice_extractor import extract_invoice_fields


def test_extracts_invoice_fields() -> None:
    text = (
        "Factura número F-2026-001 "
        "Fecha de emisión 28/10/2026 "
        "Emisor Empresa Demo CIF B12345678 "
        "Receptor Cliente Demo NIF 12345678Z "
        "Base imponible 100,00 EUR "
        "IVA 21,00 EUR "
        "Total factura 121,00 EUR"
    )

    result = extract_invoice_fields(text)

    assert result["invoice_number"].value == "F-2026-001"
    assert result["issue_date"].value == "28/10/2026"
    assert result["issuer_tax_id"].value == "B12345678"
    assert result["recipient_tax_id"].value == "12345678Z"
    assert result["subtotal"].value == "100.00"
    assert result["tax"].value == "21.00"
    assert result["total"].value == "121.00"
    assert result["currency"].value == "EUR"