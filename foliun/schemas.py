from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard API error response."""

    error: str
    detail: str


class DocumentUploadResponse(BaseModel):
    """Response returned after document upload."""

    document_id: UUID
    status: str
    status_url: str
    duplicate: bool = False


class DocumentStatusResponse(BaseModel):
    """Document ingestion status response."""

    document_id: UUID
    filename: str
    status: str
    chunk_count: int | None = None
    error_message: str | None = None


class DocumentListItem(BaseModel):
    """Document list item."""

    document_id: UUID
    filename: str
    status: str
    uploaded_at: datetime
    chunk_count: int


class HealthResponse(BaseModel):
    """System health response."""

    status: str
    dependencies: dict[str, str]


class QueryRequest(BaseModel):
    """Query request body."""

    query: str = Field(min_length=1, max_length=2000)
    model: str = "gemma-4-2b"


class RetrievedChunk(BaseModel):
    """Retrieved chunk returned by the retrieval pipeline."""

    content: str
    document_id: UUID
    document_title: str
    page_number: int | None
    section_header: str | None
    chunk_index: int
    score: float
    rrf_score: float | None = None


class RetrievalResult(BaseModel):
    """Retrieval pipeline result."""

    chunks: list[RetrievedChunk]
    insufficient_context: bool = False
    reason: str | None = None
    reranking_skipped: bool = False
    total_candidates: int = 0
    latency_ms: float = 0.0
