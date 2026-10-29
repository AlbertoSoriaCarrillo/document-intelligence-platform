import pytest
from fastapi.testclient import TestClient

from app.extraction.invoice_extractor import extract_invoice_fields
from app.extraction.ocr_layout import OcrWord
from app.extraction.text_extractor import TextExtractionResult
from app.main import app


def word(text, x, y, confidence=95):
    return OcrWord(text, confidence, x, y, x + 0.05, y + 0.01, 1, 1, 1)


def party(label, value, x, y):
    return [word(label, x, y), word('NIF', x, y + 0.04), word(value, x + 0.06, y + 0.04)]


@pytest.mark.parametrize('issuer,recipient', [
    ((0.1, 0.2), (0.6, 0.2)),
    ((0.6, 0.2), (0.1, 0.2)),
    ((0.1, 0.2), (0.1, 0.5)),
    ((0.1, 0.5), (0.1, 0.2)),
])
def test_roles_follow_headings_not_order(issuer, recipient):
    words = party('PROVEEDOR', 'B12345678', *issuer) + party('CLIENTE', '12345678Z', *recipient)
    fields = extract_invoice_fields('Factura', [list(reversed(words))])
    assert fields['issuer_tax_id'].value == 'B12345678'
    assert fields['recipient_tax_id'].value == '12345678Z'


def test_corrected_ids_are_doubtful():
    fields = extract_invoice_fields('Factura', [
        party('EMISOR', 'BO0000000', 0.1, 0.2) + party('RECEPTOR', 'BO0000001', 0.6, 0.2)
    ])
    assert fields['issuer_tax_id'].value == 'B00000000'
    assert fields['recipient_tax_id'].value == 'B00000001'
    assert fields['issuer_tax_id'].status.value == 'doubtful'
    assert fields['recipient_tax_id'].status.value == 'doubtful'


def test_no_role_without_heading_even_if_flattened_text_suggests_one():
    fields = extract_invoice_fields('Emisor B12345678', [[word('B12345678', 0.1, 0.2)]])
    assert fields['issuer_tax_id'].value is None


def test_regions_are_never_compared():
    fields = extract_invoice_fields('Factura', [[word('EMISOR', 0.1, 0.2)], [word('B12345678', 0.1, 0.24)]])
    assert fields['issuer_tax_id'].value is None


def test_equal_distance_to_roles_is_ambiguous():
    fields = extract_invoice_fields('Factura', [[
        word('EMISOR', 0.1, 0.2), word('RECEPTOR', 0.3, 0.2), word('B12345678', 0.2, 0.24)
    ]])
    assert fields['issuer_tax_id'].value is None
    assert fields['recipient_tax_id'].value is None


def test_conflicting_ids_in_multiple_regions_are_missing():
    fields = extract_invoice_fields('Factura', [
        party('EMISOR', 'B12345678', 0.1, 0.2), party('EMISOR', 'B87654321', 0.1, 0.2)
    ])
    assert fields['issuer_tax_id'].value is None


def test_low_confidence_id_is_doubtful():
    fields = extract_invoice_fields('Factura', [[word('EMISOR', 0.1, 0.2), word('B12345678', 0.1, 0.24, 65)]])
    assert fields['issuer_tax_id'].status.value == 'doubtful'


def test_endpoint_passes_layout_to_extractor(monkeypatch):
    result = TextExtractionResult(
        text='Factura Base imponible IVA Total', method='ocr', warnings=[],
        ocr_regions=[party('EMISOR', 'BO0000000', 0.6, 0.2) + party('RECEPTOR', 'BO0000001', 0.1, 0.2)],
    )
    monkeypatch.setattr('app.api.document_routes.extract_text_from_image', lambda _: result)
    response = TestClient(app).post('/api/documents/inspect', files={'file': ('invoice.jpg', b'test', 'image/jpeg')})
    assert response.status_code == 200
    fields = response.json()['extracted_fields']
    assert fields['issuer_tax_id'] == {'value': 'B00000000', 'status': 'doubtful'}
    assert fields['recipient_tax_id'] == {'value': 'B00000001', 'status': 'doubtful'}
