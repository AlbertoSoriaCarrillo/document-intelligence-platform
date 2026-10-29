from dataclasses import dataclass

import pymupdf


class DocumentProcessingError(Exception):
    """The supplied document cannot be inspected."""


@dataclass
class TextExtractionResult:
    text: str
    method: str
    warnings: list[str]


def extract_text_from_pdf(content: bytes) -> TextExtractionResult:
    if not content.startswith(b"%PDF-"):
        raise DocumentProcessingError("The file content is not a PDF.")
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass:
                raise DocumentProcessingError("The PDF is password protected and cannot be read.")
            if not document.page_count:
                raise DocumentProcessingError("The PDF contains no pages.")
            parts = [page.get_text("text").strip() for page in document]
            if any(not part for part in parts):
                raise DocumentProcessingError("Every PDF page must have a readable text layer; scanned PDFs are unsupported.")
            warnings = ["The PDF was repaired while reading; verify the extracted values."] if document.is_repaired else []
            return TextExtractionResult("\n\n".join(parts), "native_text", warnings)
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError("The PDF is corrupt or cannot be read.") from exc
