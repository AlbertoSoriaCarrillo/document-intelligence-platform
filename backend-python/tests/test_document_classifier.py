import pytest

from app.classification.document_classifier import classify_document
from app.models.document import DocumentType


@pytest.mark.parametrize(
    ("text", "expected_type"),
    [
        (
            "Documento Nacional de Identidad. Apellidos. Nacionalidad. Validez.",
            DocumentType.DNI,
        ),
        (
            "Factura número 42. Base imponible. IVA. Total.",
            DocumentType.INVOICE,
        ),
        (
            "Albarán de entrega. Pedido. Mercancía. Recibido por.",
            DocumentType.DELIVERY_NOTE,
        ),
        (
            "Ticket de compra. Caja. Efectivo. Cambio. Total.",
            DocumentType.RECEIPT,
        ),
    ],
)
def test_classifies_supported_documents(
    text: str,
    expected_type: DocumentType,
) -> None:
    result = classify_document(text)

    assert result.document_type == expected_type


def test_returns_unknown_for_unrecognized_text() -> None:
    result = classify_document("Texto sin información relevante.")

    assert result.document_type == DocumentType.UNKNOWN