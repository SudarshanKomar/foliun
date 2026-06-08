import logging
import time
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from foliun.config import Settings, get_settings
from foliun.models import Chunk, Document, DocumentStatus
from foliun.services.chunking import get_token_counter, split_text_into_chunks
from foliun.services.embeddings import Embedder, get_embedder
from foliun.services.text_extraction import extract_text

logger = logging.getLogger(__name__)


def process_document(
    document_id: UUID,
    db: Session,
    embedder: Embedder | None = None,
    settings: Settings | None = None,
    mark_failed_on_error: bool = True,
) -> None:
    """Process a document through extraction, chunking, embedding, and storage."""

    config = settings or get_settings()
    document = db.get(Document, document_id)
    if document is None:
        raise ValueError(f"Document {document_id} not found")
    started = time.perf_counter()
    document.status = DocumentStatus.processing
    document.error_message = None
    db.commit()
    try:
        db.execute(delete(Chunk).where(Chunk.document_id == document_id))
        extraction_started = time.perf_counter()
        extracted = extract_text(Path(document.file_path), document.mime_type)
        if not extracted.text.strip():
            document.status = DocumentStatus.failed
            document.error_message = "No extractable text found. The document may be scanned/image-based."
            db.commit()
            return
        logger.info(
            "Ingestion stage completed",
            extra={
                "document_id": str(document_id),
                "stage": "extraction",
                "duration_ms": round((time.perf_counter() - extraction_started) * 1000, 2),
                "outcome": "success",
            },
        )
        chunk_started = time.perf_counter()
        counter = get_token_counter(config)
        text_chunks = split_text_into_chunks(extracted.text, extracted.page_offsets, counter, config)
        if not text_chunks:
            document.status = DocumentStatus.failed
            document.error_message = "Text extraction succeeded but produced no valid chunks"
            db.commit()
            return
        logger.info(
            "Ingestion stage completed",
            extra={
                "document_id": str(document_id),
                "stage": "chunking",
                "duration_ms": round((time.perf_counter() - chunk_started) * 1000, 2),
                "chunk_count": len(text_chunks),
                "outcome": "success",
            },
        )
        embedding_started = time.perf_counter()
        active_embedder = embedder or get_embedder()
        vectors = active_embedder.embed_texts([chunk.content for chunk in text_chunks])
        if any(len(vector) != config.embedding_dimensions for vector in vectors):
            raise RuntimeError("Embedding generation produced incompatible dimensions")
        logger.info(
            "Ingestion stage completed",
            extra={
                "document_id": str(document_id),
                "stage": "embedding",
                "duration_ms": round((time.perf_counter() - embedding_started) * 1000, 2),
                "embedding_model": config.embedding_model_name,
                "outcome": "success",
            },
        )
        storage_started = time.perf_counter()
        chunks = [
            Chunk(
                document_id=document_id,
                chunk_index=index,
                content=text_chunk.content,
                token_count=text_chunk.token_count,
                page_number=text_chunk.page_number,
                section_header=text_chunk.section_header,
                char_start=text_chunk.char_start,
                char_end=text_chunk.char_end,
                embedding=vectors[index],
            )
            for index, text_chunk in enumerate(text_chunks)
        ]
        db.add_all(chunks)
        document.status = DocumentStatus.ready
        document.page_count = extracted.page_count
        db.commit()
        logger.info(
            "Ingestion job completed",
            extra={
                "document_id": str(document_id),
                "stage": "storage",
                "duration_ms": round((time.perf_counter() - storage_started) * 1000, 2),
                "total_duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "chunk_count": len(chunks),
                "outcome": "success",
            },
        )
    except Exception as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document is not None:
            document.status = DocumentStatus.failed if mark_failed_on_error else DocumentStatus.processing
            document.error_message = str(exc)
            db.commit()
        logger.exception(
            "Ingestion job failed",
            extra={"document_id": str(document_id), "stage": "ingestion", "outcome": "failure"},
        )
        raise


def chunk_count_for_document(db: Session, document_id: UUID) -> int:
    """Return chunk count for a document."""

    return db.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)) or 0
