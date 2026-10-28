from app.extraction.mrz_parser import parse_td1_mrz


def test_parses_td1_mrz() -> None:
    text = (
        "IDESPABC123456<<<<<<<<<<<<<<< "
        "9001011M3001019ESP<<<<<<<<<<<0 "
        "PEREZ<GARCIA<<JUAN<TEST<<<<<<"
    )

    result = parse_td1_mrz(text)

    assert result is not None
    assert result.name == "JUAN TEST"
    assert result.surnames == "PEREZ GARCIA"
    assert result.birth_date == "01/01/1990"
    assert result.expiry_date == "01/01/2030"
    assert result.sex == "M"
    assert result.nationality == "ESP"


def test_returns_none_without_mrz() -> None:
    assert parse_td1_mrz("Documento sin MRZ") is None