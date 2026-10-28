from fastapi import APIRouter, File, HTTPException, UploadFile, status
from app.classification.document_classifier import classify_document
from app.core.config import ALLOWED_CONTENT_TYPES, MAX_UPLOAD_SIZE
from app.extraction.text_extractor import (
    DocumentProcessingError,
    extract_text_from_image,
    extract_text_from_pdf,
)
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
    content_type = file.content_type or ""

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported formats are PDF, JPEG and PNG.",
        )

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
        if content_type == "application/pdf":
            extraction = extract_text_from_pdf(content)
        else:
            extraction = extract_text_from_image(content)

    except DocumentProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    classification = classify_document(extraction.text)

    return DocumentInspectionResponse(
        filename=file.filename or "unnamed-document",
        content_type=content_type,
        size=len(content),
        character_count=len(extraction.text),
        extraction_method=extraction.method,
        text_preview=extraction.text[:500],
        warnings=extraction.warnings,
        classification=classification,
    )