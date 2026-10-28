import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MrzData:
    name: str | None
    surnames: str | None
    birth_date: str | None
    expiry_date: str | None
    sex: str | None
    nationality: str | None


def _parse_date(
    value: str,
    *,
    birth_date: bool,
) -> str | None:
    year_number = int(value[0:2])
    month = int(value[2:4])
    day = int(value[4:6])

    if birth_date:
        current_short_year = date.today().year % 100
        century = 1900 if year_number > current_short_year else 2000
        year = century + year_number
    else:
        year = 2000 + year_number

    try:
        parsed = date(year, month, day)
    except ValueError:
        return None

    return parsed.strftime("%d/%m/%Y")


def _clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("<", " ")).strip()


def parse_td1_mrz(text: str) -> MrzData | None:
    compact = re.sub(
        r"[^A-Z0-9<]",
        "",
        text.upper(),
    )

    second_line = re.search(
        r"(\d{6})\d([MF<])(\d{6})\d([A-Z]{3})",
        compact,
    )

    if not second_line:
        return None

    birth_value = second_line.group(1)
    sex_value = second_line.group(2)
    expiry_value = second_line.group(3)
    nationality = second_line.group(4)

    remaining_text = compact[second_line.end():]

    names_match = re.search(
        r"([A-Z]+(?:<[A-Z]+)*)<<"
        r"([A-Z]+(?:<[A-Z]+)*)",
        remaining_text,
    )

    surnames = None
    name = None

    if names_match:
        surnames = _clean_name(names_match.group(1))
        name = _clean_name(names_match.group(2))

    return MrzData(
        name=name,
        surnames=surnames,
        birth_date=_parse_date(
            birth_value,
            birth_date=True,
        ),
        expiry_date=_parse_date(
            expiry_value,
            birth_date=False,
        ),
        sex=None if sex_value == "<" else sex_value,
        nationality=nationality,
    )