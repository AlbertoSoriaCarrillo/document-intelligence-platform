from app.models.document import ExtractedField, FieldStatus
from app.extraction.mrz_parser import parse_td1_mrz

import re


DATE_PATTERN = r"\b\d{2}(?:[./-]|\s)\d{2}(?:[./-]|\s)\d{4}\b"


def _found(value: str) -> ExtractedField:
    return ExtractedField(
        value=value,
        status=FieldStatus.FOUND,
    )


def _missing() -> ExtractedField:
    return ExtractedField(
        value=None,
        status=FieldStatus.MISSING,
    )


def extract_dni_fields(
    text: str,
) -> dict[str, ExtractedField]:
    normalized = re.sub(r"\s+", " ", text).strip()
    mrz = parse_td1_mrz(text)

    document_number_match = re.search(
        r"\b(?:\d{8}\s*[A-Z]|[XYZ]\s*\d{7}\s*[A-Z])\b",
        normalized,
        re.IGNORECASE,
    )

    nationality_match = re.search(
        r"\b(?:ESP|ESPAÑA)\b",
        normalized,
        re.IGNORECASE,
    )

    support_number_match = re.search(
        r"\b[A-Z]{3}\d{6}\b",
        normalized,
        re.IGNORECASE,
    )

    sex_match = re.search(
        r"\b(?:SEXO|SEX).{0,8}\b([MF])\b",
        normalized,
        re.IGNORECASE,
    )

    birth_date_match = re.search(
        rf"(?:NACIMIENTO|FECHA DE NACIMIENTO|NAC).{{0,20}}"
        rf"({DATE_PATTERN})",
        normalized,
        re.IGNORECASE,
    )

    expiry_date_match = re.search(
        rf"(?:VALIDEZ|CADUCIDAD|VÁLIDO HASTA).{{0,20}}"
        rf"({DATE_PATTERN})",
        normalized,
        re.IGNORECASE,
    )

    issue_date_match = re.search(
        rf"(?:EXPEDICIÓN|EXPEDICION|FECHA DE EXPEDICIÓN).{{0,20}}"
        rf"({DATE_PATTERN})",
        normalized,
        re.IGNORECASE,
    )

    detected_dates = re.findall(
        DATE_PATTERN,
        normalized,
        re.IGNORECASE,
    )

    return {
        "document_number": (
            _found(
                re.sub(
                    r"\s+",
                    "",
                    document_number_match.group(0),
                ).upper()
            )
            if document_number_match
            else _missing()
        ),
        "nationality": (
            _found(nationality_match.group(0).upper())
            if nationality_match
            else _found(mrz.nationality)
            if mrz and mrz.nationality
            else _missing()
        ),
        "support_number": (
            _found(support_number_match.group(0).upper())
            if support_number_match
            else _missing()
        ),
        "sex": (
            _found(sex_match.group(1).upper())
            if sex_match
            else _found(mrz.sex)
            if mrz and mrz.sex
            else _missing()
        ),
        "birth_date": (
            _found(birth_date_match.group(1))
            if birth_date_match
            else _found(mrz.birth_date)
            if mrz and mrz.birth_date
            else _missing()
        ),
        "expiry_date": (
            _found(expiry_date_match.group(1))
            if expiry_date_match
            else _found(mrz.expiry_date)
            if mrz and mrz.expiry_date
            else _missing()
        ),
        "issue_date": (
            _found(issue_date_match.group(1))
            if issue_date_match
            else _missing()
        ),
        "detected_dates": ExtractedField(
            value=", ".join(detected_dates) or None,
            status=(
                FieldStatus.DOUBTFUL
                if detected_dates
                else FieldStatus.MISSING
            ),
        ),
        "name": (
            _found(mrz.name)
            if mrz and mrz.name
            else _missing()
        ),
        "surnames": (
            _found(mrz.surnames)
            if mrz and mrz.surnames
            else _missing()
        ),
    }