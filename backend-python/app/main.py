from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.document_routes import router as document_router


app = FastAPI(
    title="Document Intelligence API",
    description="Text-layer invoice inspection for the Lumenia sample structure.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(document_router)


@app.get("/api/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "document-intelligence-api",
    }