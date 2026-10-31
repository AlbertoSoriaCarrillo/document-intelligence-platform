from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.extraction.invoice_extractor import extract_invoice_fields
from app.extraction.text_extractor import extract_text_from_pdf

client = TestClient(app)
SAMPLE = Path(__file__).resolve().parents[2] / "docs/factura_luz_simulada_lumenia.pdf"


def pdf(text=None, password=None):
    with pymupdf.open() as document:
        page = document.new_page()
        if text:
            page.insert_text((40, 40), text.replace("\u20ac", "EUR"), fontsize=8)
        if password:
            return document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password)
        return document.tobytes()


def inspect(content, name="arbitrary.bin", mime="application/octet-stream"):
    return client.post("/api/documents/inspect", files={"file": (name, content, mime)})


def test_lumenia_integration():
    response = inspect(SAMPLE.read_bytes())
    assert response.status_code == 200
    body = response.json()
    assert "classification" not in body
    assert body["extraction_method"] == "native_text"
    fields = body["extracted_fields"]
    assert "detected_tax_ids" not in fields
    for key, value in {"invoice_number": "LU-2026-00428", "issue_date": "28/10/2026",
                       "issuer_tax_id": "B00000000", "recipient_tax_id": "B00000001",
                       "subtotal": "52.29", "tax": "10.98", "total": "63.27", "currency": "EUR"}.items():
        assert fields[key] == {"value": value, "status": "found"}
    lines = fields["line_items"]
    assert lines["status"] == "doubtful"
    assert [i["description"]["value"] for i in lines["value"]] == [
        "Potencia contratada", "Energ\u00eda consumida", "Impuesto el\u00e9ctrico (simulado)",
        "Alquiler del contador", "Servicio de asistencia"]
    assert [i["amount"]["value"] for i in lines["value"]] == ["14.49", "31.16", "2.33", "0.81", "3.50"]
    assert lines["value"][2]["quantity"] == {"value": None, "status": "missing"}
    assert lines["value"][2]["unit_price"]["status"] == "doubtful"


def test_other_values_and_incomplete_compatible_invoice():
    text = extract_text_from_pdf(SAMPLE.read_bytes()).text
    for old, new in {"LU-2026-00428": "NEW-2030-987", "28/10/2026": "03/02/2030",
                     "B00000000": "B87654321", "B00000001": "12345678Z",
                     "52,29": "200,00", "10,98": "42,00", "63,27": "242,00",
                     "186 kWh": "250 kWh", "31,16": "41,88"}.items():
        text = text.replace(old, new)
    response = inspect(pdf(text))
    assert response.status_code == 200
    fields = response.json()["extracted_fields"]
    for key, value in {"invoice_number": "NEW-2030-987", "issue_date": "03/02/2030",
                       "issuer_tax_id": "B87654321", "recipient_tax_id": "12345678Z",
                       "subtotal": "200.00", "tax": "42.00", "total": "242.00"}.items():
        assert fields[key]["value"] == value
    assert fields["line_items"]["value"][1]["quantity"]["value"] == "250 kWh"
    assert fields["line_items"]["value"][1]["amount"]["value"] == "41.88"
    text = text.replace("NEW-2030-987", "").replace("B87654321", "").replace("200,00 EUR", "")
    response = inspect(pdf(text))
    assert response.status_code == 200
    fields = response.json()["extracted_fields"]
    for key in ("invoice_number", "issuer_tax_id", "subtotal"):
        assert fields[key] == {"value": None, "status": "missing"}
    assert fields["recipient_tax_id"]["value"] == "12345678Z"


def test_false_positive_and_ambiguous_fields():
    fields = extract_invoice_fields("Factura Fecha de emisi\u00f3n: 28/10/2026 Emisor CIF Receptor NIF B12345678")
    assert fields.invoice_number.status == "missing"
    assert fields.issuer_tax_id.status == "missing"
    assert fields.recipient_tax_id.value == "B12345678"
    fields = extract_invoice_fields("Factura n\u00famero: A-123\nFactura n\u00famero: B-456\nEmisor CIF B12345678 CIF B87654321\nReceptor")
    assert fields.invoice_number.status == "doubtful"
    assert fields.issuer_tax_id.status == "doubtful"


@pytest.mark.parametrize("content,message", [
    (b"not a pdf", "no es un PDF"),
    (b"%PDF-1.7\ncorrupt", "está dañado"),
    (pdf(password="secret"), "protegido con contraseña"),
    (pdf(), "capa de texto legible"),
    (pdf("Unrelated text document"), "estructura esperada"),
])
def test_invalid_documents(content, message):
    response = inspect(content, "invoice.pdf", "application/pdf")
    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_empty_and_oversized(monkeypatch):
    assert inspect(b"").status_code == 400
    monkeypatch.setattr("app.api.document_routes.MAX_UPLOAD_SIZE", 10)
    assert inspect(b"x" * 11).status_code == 413


def test_cors():
    response = client.options("/api/documents/inspect", headers={"Origin": "http://localhost:4200", "Access-Control-Request-Method": "POST"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
