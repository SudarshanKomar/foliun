import uuid

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from foliun.auth import require_api_key
from foliun.config import get_settings
from foliun.db import get_db
from foliun.errors import ApiError
from foliun.models import Chunk, Document, DocumentStatus
from foliun.schemas import DocumentListItem, DocumentStatusResponse, DocumentUploadResponse
from foliun.services.files import read_and_validate_upload, sha256_bytes, store_document_file
from foliun.services.ingestion import chunk_count_for_document

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> DocumentUploadResponse:
    """Accept a document upload and enqueue ingestion."""

    settings = get_settings()
    content, filename = await read_and_validate_upload(file, settings)
    file_hash = sha256_bytes(content)
    existing = db.scalar(select(Document).where(Document.filename == filename, Document.file_hash == file_hash))
    if existing:
        return DocumentUploadResponse(document_id=existing.id, status=existing.status.value, status_url=f"/api/v1/documents/{existing.id}/status", duplicate=True)
    document_id = uuid.uuid4()
    try:
        stored_path = store_document_file(content, filename, str(document_id), settings)
    except OSError as exc:
        raise ApiError(500, "internal_error", "An unexpected error occurred") from exc
    document = Document(
        id=document_id,
        filename=filename,
        file_path=str(stored_path),
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
        file_hash=file_hash,
        status=DocumentStatus.pending,
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Document).where(Document.filename == filename, Document.file_hash == file_hash))
        if existing:
            return DocumentUploadResponse(document_id=existing.id, status=existing.status.value, status_url=f"/api/v1/documents/{existing.id}/status", duplicate=True)
        raise
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await redis.enqueue_job("process_document_job", str(document.id))
    await redis.close()
    return DocumentUploadResponse(document_id=document.id, status=document.status.value, status_url=f"/api/v1/documents/{document.id}/status")


@router.get("", response_model=list[DocumentListItem])
def list_documents(db: Session = Depends(get_db)) -> list[DocumentListItem]:
    """List uploaded documents."""

    rows = db.query(Document, func.count(Chunk.id).label("chunk_count")).outerjoin(Chunk, Chunk.document_id == Document.id).group_by(Document.id).order_by(Document.created_at.desc()).all()
    return [DocumentListItem(document_id=document.id, filename=document.filename, status=document.status.value, uploaded_at=document.created_at, chunk_count=chunk_count) for document, chunk_count in rows]


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(document_id: uuid.UUID, db: Session = Depends(get_db)) -> DocumentStatusResponse:
    """Return document ingestion status."""

    document = db.get(Document, document_id)
    if document is None:
        raise ApiError(404, "not_found", "Endpoint not found")
    return DocumentStatusResponse(document_id=document.id, filename=document.filename, status=document.status.value, chunk_count=chunk_count_for_document(db, document.id), error_message=document.error_message)
