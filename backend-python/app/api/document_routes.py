from fastapi import APIRouter, File, HTTPException, UploadFile, status
from app.core.config import MAX_UPLOAD_SIZE
from app.extraction.text_extractor import DocumentProcessingError, extract_text_from_pdf
from app.extraction.invoice_extractor import ensure_compatible_invoice, extract_invoice_fields
from app.models.document import DocumentInspectionResponse


router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"],
)


@router.post(
    "/inspect",
    response_model=DocumentInspectionResponse,
)
async def inspect_document(
    file: UploadFile = File(...),
) -> DocumentInspectionResponse:
    content = await file.read(MAX_UPLOAD_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="The maximum allowed file size is 10 MB.",
        )

    try:
        extraction = extract_text_from_pdf(content)
        ensure_compatible_invoice(extraction.text)
        extracted_fields = extract_invoice_fields(extraction.text)

    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return DocumentInspectionResponse(
        filename=file.filename or "unnamed-document",
        content_type="application/pdf",
        size=len(content),
        character_count=len(extraction.text),
        extraction_method=extraction.method,
        text_preview=extraction.text[:500],
        warnings=extraction.warnings,
        extracted_fields=extracted_fields,
    )