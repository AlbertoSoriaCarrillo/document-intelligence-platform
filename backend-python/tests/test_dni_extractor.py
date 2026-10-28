from app.extraction.dni_extractor import extract_dni_fields
from app.models.document import FieldStatus


def test_extracts_basic_dni_fields() -> None:
    result = extract_dni_fields(
        "DNI 12345678Z Nacionalidad ESP "
        "Fecha de nacimiento 01/02/1990"
    )

    assert result["document_number"].value == "12345678Z"
    assert result["nationality"].value == "ESP"
    assert result["birth_date"].value == "01/02/1990"
    assert result["document_number"].status == FieldStatus.FOUND