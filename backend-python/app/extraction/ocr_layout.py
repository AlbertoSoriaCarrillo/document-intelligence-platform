from dataclasses import dataclass


@dataclass(frozen=True)
class OcrWord:
    text: str
    confidence: float
    left: float
    top: float
    right: float
    bottom: float
    block: int
    paragraph: int
    line: int


def extract_positioned_words(
    data: dict,
    image_width: int,
    image_height: int,
) -> list[OcrWord]:
    """Conserva texto, confianza y posición relativa de cada palabra."""
    if image_width <= 0 or image_height <= 0:
        raise ValueError("Image dimensions must be positive.")

    words: list[OcrWord] = []

    for index, raw_text in enumerate(data["text"]):
        text = raw_text.strip()

        if not text:
            continue

        confidence = float(data["conf"][index])

        if confidence < 0:
            continue

        left = int(data["left"][index])
        top = int(data["top"][index])
        width = int(data["width"][index])
        height = int(data["height"][index])

        words.append(
            OcrWord(
                text=text,
                confidence=confidence,
                left=left / image_width,
                top=top / image_height,
                right=(left + width) / image_width,
                bottom=(top + height) / image_height,
                block=int(data["block_num"][index]),
                paragraph=int(data["par_num"][index]),
                line=int(data["line_num"][index]),
            )
        )

    return words


def group_words_into_rows(
    words: list[OcrWord],
) -> list[list[OcrWord]]:
    usable_words = [
        word
        for word in words
        if word.text.strip()
        and word.confidence >= 35
        and word.bottom > word.top
    ]

    ordered_words = sorted(
        usable_words,
        key=lambda word: (
            (word.top + word.bottom) / 2,
            word.left,
        ),
    )

    rows: list[list[OcrWord]] = []

    for word in ordered_words:
        center = (word.top + word.bottom) / 2
        height = word.bottom - word.top
        candidates: list[tuple[float, int]] = []

        for index, row in enumerate(rows):
            row_center = sum(
                (item.top + item.bottom) / 2
                for item in row
            ) / len(row)

            row_height = sum(
                item.bottom - item.top
                for item in row
            ) / len(row)

            distance = abs(center - row_center)
            tolerance = 0.5 * min(height, row_height)

            if distance <= tolerance:
                candidates.append((distance, index))

        if candidates:
            _, nearest_row = min(candidates)
            rows[nearest_row].append(word)
        else:
            rows.append([word])

    for row in rows:
        row.sort(key=lambda word: word.left)

    rows.sort(
        key=lambda row: sum(
            (word.top + word.bottom) / 2
            for word in row
        ) / len(row)
    )

    return rows