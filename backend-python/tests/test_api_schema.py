from app.main import app


def test_invoice_fields_are_explicit_in_openapi():
    schemas = app.openapi()["components"]["schemas"]
    fields = schemas["InvoiceFields"]
    expected = {"invoice_number", "issue_date", "issuer_tax_id", "recipient_tax_id",
                "subtotal", "tax", "total", "currency", "line_items"}
    assert set(fields["properties"]) == expected
    assert set(fields["required"]) == expected
    assert schemas["DocumentInspectionResponse"]["properties"]["extracted_fields"]["$ref"].endswith("/InvoiceFields")
