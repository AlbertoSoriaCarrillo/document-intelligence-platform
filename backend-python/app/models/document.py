from pydantic import BaseModel


class DocumentInspectionResponse(BaseModel):
    filename: str
    content_type: str
    size: int
    character_count: int
    extraction_method: str
    text_preview: str
    warnings: list[str]