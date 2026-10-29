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