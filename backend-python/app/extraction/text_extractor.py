from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps
from app.core.settings import BACKEND_DIR, get_settings

import fitz
import pytesseract
import os
import shutil


class DocumentProcessingError(Exception):
    """Raised when a document cannot be processed."""


@dataclass
class TextExtractionResult:
    text: str
    method: str
    warnings: list[str]

def _configure_tesseract() -> str:
    settings = get_settings()

    executable = (
        settings.tesseract_cmd
        or shutil.which("tesseract")
    )

    if not executable:
        raise DocumentProcessingError(
            "Tesseract OCR is not installed or is not available in PATH."
        )

    pytesseract.pytesseract.tesseract_cmd = executable

    if settings.tessdata_dir:
        tessdata_path = Path(settings.tessdata_dir)

        if not tessdata_path.is_absolute():
            tessdata_path = BACKEND_DIR / tessdata_path

        tessdata_path = tessdata_path.resolve()

        if not tessdata_path.exists():
            raise DocumentProcessingError(
                "The configured Tesseract language directory does not exist."
            )

        os.environ["TESSDATA_PREFIX"] = (
            str(tessdata_path) + os.sep
        )

    return settings.ocr_language

def _ocr_image(image: Image.Image) -> str:
    language = _configure_tesseract()

    prepared_image = ImageOps.autocontrast(
        ImageOps.grayscale(image)
    )

    try:
        return pytesseract.image_to_string(
            prepared_image,
            lang=language,
            config="--oem 1 --psm 6",
        ).strip()

    except pytesseract.TesseractError as exc:
        raise DocumentProcessingError(
            f"The OCR engine failed with exit code {exc.status}."
        ) from exc

def extract_text_from_pdf(content: bytes) -> TextExtractionResult:
    try:
        native_parts: list[str] = []
        ocr_parts: list[str] = []

        with fitz.open(stream=content, filetype="pdf") as document:
            for page in document:
                native_text = page.get_text("text").strip()

                if native_text:
                    native_parts.append(native_text)
                    continue

                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(2.5, 2.5),
                    alpha=False,
                )

                image = Image.open(
                    BytesIO(pixmap.tobytes("png"))
                )

                ocr_text = _ocr_image(image)

                if ocr_text:
                    ocr_parts.append(ocr_text)

        combined_parts = native_parts + ocr_parts
        text = "\n\n".join(combined_parts).strip()

        if native_parts and ocr_parts:
            method = "hybrid"
        elif ocr_parts:
            method = "ocr"
        elif native_parts:
            method = "native_text"
        else:
            method = "none"

        warnings: list[str] = []

        if ocr_parts:
            warnings.append(
                "OCR was used because one or more pages had no text layer."
            )

        if not text:
            warnings.append(
                "No readable text could be extracted from the document."
            )

        return TextExtractionResult(
            text=text,
            method=method,
            warnings=warnings,
        )

    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(
            "The PDF document could not be processed."
        ) from exc

def extract_text_from_image(
    content: bytes,
) -> TextExtractionResult:
    try:
        with Image.open(BytesIO(content)) as image:
            text = _ocr_image(image)

        warnings = ["OCR was used to process the image."]

        if not text:
            warnings.append(
                "No readable text could be extracted from the image."
            )

        return TextExtractionResult(
            text=text,
            method="ocr" if text else "none",
            warnings=warnings,
        )

    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(
            "The image could not be processed."
        ) from exc