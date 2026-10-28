from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.extraction.text_extractor import TextExtractionResult
from app.main import app


client = TestClient(app)


def test_inspects_and_extracts_dni(
    monkeypatch: MonkeyPatch,
) -> None:
    fake_text = (
        "Documento Nacional de Identidad "
        "DNI 12345678Z Nacionalidad ESP "
        "IDESPABC123456<<<<<<<<<<<<<<< "
        "9001011M3001019ESP<<<<<<<<<<<0 "
        "PEREZ<GARCIA<<JUAN<TEST<<<<<<"
    )

    def fake_pdf_extractor(
        content: bytes,
    ) -> TextExtractionResult:
        return TextExtractionResult(
            text=fake_text,
            method="ocr",
            warnings=["OCR used for test."],
        )

    monkeypatch.setattr(
        "app.api.document_routes.extract_text_from_pdf",
        fake_pdf_extractor,
    )

    response = client.post(
        "/api/documents/inspect",
        files={
            "file": (
                "test-dni.pdf",
                b"synthetic-pdf-content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["classification"]["document_type"] == "dni"
    assert (
        body["extracted_fields"]["document_number"]["value"]
        == "12345678Z"
    )
    assert (
        body["extracted_fields"]["birth_date"]["value"]
        == "01/01/1990"
    )
    assert (
        body["extracted_fields"]["expiry_date"]["value"]
        == "01/01/2030"
    )
    assert body["extracted_fields"]["name"]["value"] == "JUAN TEST"