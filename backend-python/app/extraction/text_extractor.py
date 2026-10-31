from dataclasses import dataclass

import pymupdf

from app.core.messages import get_message
from app.extraction.errors import DocumentProcessingError


@dataclass
class TextExtractionResult:
    """Texto en orden de páginas, método de lectura y avisos para el consumidor."""
    text: str
    method: str
    warnings: list[str]


def extract_text_from_pdf(content: bytes) -> TextExtractionResult:
    """Lee los bytes de un PDF con texto sin guardar el documento en disco.

    Conserva saltos de línea y orden de páginas para el extractor de conceptos.
    No aplica OCR ni comprueba la estructura de la factura.

    Raises:
        DocumentProcessingError: contenido no PDF, protegido, vacío, ilegible
            o con alguna página sin texto extraíble.
    """
    # La cabecera es un primer filtro; PyMuPDF comprueba después si puede abrirlo.
    if not content.startswith(b"%PDF-"):
        raise DocumentProcessingError(get_message("not_pdf"))
    try:
        with pymupdf.open(stream=content, filetype="pdf") as document:
            if document.needs_pass:
                raise DocumentProcessingError(get_message("protected_pdf"))
            if not document.page_count:
                raise DocumentProcessingError(get_message("empty_pdf"))
            parts = [page.get_text("text").strip() for page in document]
            # No se devuelve silenciosamente una factura parcial si una página no es legible.
            if any(not part for part in parts):
                raise DocumentProcessingError(get_message("scanned_pdf"))
            warnings = [get_message("repaired_pdf")] if document.is_repaired else []
            return TextExtractionResult("\n\n".join(parts), "native_text", warnings)
    # Preservar los errores de dominio permite comunicarlos claramente por HTTP.
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(get_message("invalid_pdf")) from exc
