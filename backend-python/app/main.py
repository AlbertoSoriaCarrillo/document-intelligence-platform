from fastapi import FastAPI

app = FastAPI(
    title="Document Intelligence API",
    description="API for document classification and structured data extraction.",
    version="0.1.0",
)


@app.get("/api/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "document-intelligence-api",
    }