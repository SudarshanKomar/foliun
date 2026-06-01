# Document Ingestion Specification

## Context
The AI Research Workspace requires a reliable pipeline for ingesting PDF and plain text documents into the system. Users upload documents through the API, and the system must validate, extract text, split into chunks with metadata, and persist the results for downstream embedding and retrieval. This is the foundational write-path of the RAG system — all retrieval quality depends on the quality of ingestion.

Document ingestion is inherently asynchronous: text extraction and chunking can take seconds to minutes for large PDFs, so uploads must return immediately while processing continues in the background. Users need visibility into ingestion progress and failures.

## Requirements

### Functional Requirements
- FR-1: Accept PDF and TXT file uploads via multipart/form-data POST request. Return `202 Accepted` with document ID and status URL immediately.
- FR-2: Validate uploaded files synchronously before acceptance: file type must be PDF (application/pdf) or TXT (text/plain), file size must be ≤ 50MB, file must be non-empty.
- FR-3: Store uploaded files to local filesystem at `./storage/documents/{document_uuid}/{original_filename}`.
- FR-4: Extract text content from PDF files using PyMuPDF (fitz). For TXT files, read content directly with UTF-8 encoding.
- FR-5: Split extracted text into chunks of approximately 512 tokens with 20% (102 token) overlap using recursive character text splitting with separator hierarchy: `["\n\n", "\n", ". ", " ", ""]`.
- FR-6: Annotate each chunk with metadata: document title (filename without extension), section header (if detectable from heading patterns), page number (PDF only), chunk index (0-based sequential), character start offset, character end offset.
- FR-7: Persist document record in PostgreSQL with status tracking: `pending → processing → ready | failed`.
- FR-8: Persist all chunks with content and metadata in PostgreSQL (embeddings handled by spec 002).
- FR-9: Detect duplicate uploads by filename + SHA-256 file hash. If a duplicate is detected, return the existing document ID and status instead of re-processing.
- FR-10: Provide document status endpoint returning current ingestion state, chunk count (if available), and error message (if failed).
- FR-11: Provide document list endpoint returning all documents with their status, filename, upload time, and chunk count.

### Non-Functional Requirements
- NFR-1: Ingestion time must be < 30 seconds for a 10-page PDF (extraction + chunking + embedding). Extraction and chunking alone should complete in < 5 seconds; local embedding adds up to 15 seconds on CPU (see spec 002).
- NFR-2: File validation must complete in < 100ms (synchronous, in API request path).
- NFR-3: Failed ingestion jobs must retry up to 3 times with exponential backoff (1s, 4s, 16s).
- NFR-4: All ingestion failures must be logged with document ID, pipeline stage, error message, and timestamp.
- NFR-5: System must support 1,000+ documents and 100K+ chunks in PostgreSQL.
- NFR-6: File storage must be outside web-accessible paths to prevent direct file access.

## Constraints
- **Technology**: PyMuPDF (fitz) for PDF extraction, BERT WordPiece tokenizer from `BAAI/bge-base-en-v1.5` via `transformers.AutoTokenizer` for token counting (matches embedding model exactly), `arq` for job queue.
- **Scope**: Only PDF and TXT files supported. No OCR, no DOCX, no image extraction from PDFs.
- **Language**: English-language documents only. No multilingual tokenization or encoding handling beyond UTF-8.
- **Trust model**: Documents are trusted — no malware scanning, no content filtering beyond file type/size validation.
- **Dependency**: Embedding generation is handled by spec 002-embedding-and-storage. This spec creates chunks but does NOT generate embeddings.

## Failure Cases
- **Invalid file type**: Return `400 Bad Request` with error `{"error": "unsupported_file_type", "detail": "Only PDF and TXT files are supported"}`. No file is stored.
- **File too large**: Return `400 Bad Request` with error `{"error": "file_too_large", "detail": "File size exceeds 50MB limit"}`. No file is stored.
- **Empty file**: Return `400 Bad Request` with error `{"error": "empty_file", "detail": "Uploaded file is empty"}`. No file is stored.
- **PDF extraction failure**: Mark document as `failed` with error message. Retry up to 3 times. Common causes: corrupted PDF, password-protected PDF, image-only PDF (no extractable text).
- **Zero text extracted**: Mark document as `failed` with error `"No extractable text found. The document may be scanned/image-based."`. No retry.
- **Chunking produces zero chunks**: Mark document as `failed` with error `"Text extraction succeeded but produced no valid chunks"`. No retry.
- **Database write failure**: Retry the entire job. On final failure, mark as `failed` with database error.
- **File system write failure**: Return `500 Internal Server Error`. Job is not queued.
- **Duplicate document**: Return `200 OK` with existing document ID, status, and `"duplicate": true` flag.

## Success Criteria
- A valid PDF or TXT upload returns `202 Accepted` within 200ms with a document ID.
- Document status transitions from `pending` → `processing` → `ready` are trackable via status API.
- A 10-page PDF is fully ingested (extraction + chunking + embedding) in < 30 seconds.
- Chunks preserve page number attribution accurately (verified against source PDF).
- Chunk sizes are within ±10% of the 512 token target (mean chunk size between 460-564 tokens).
- Metadata (document title, page number, chunk index, character offsets) is present on all chunks.
- Duplicate uploads are detected and return the existing document without re-processing.
- Failed documents show meaningful error messages via the status API.

## Out of Scope
- Embedding generation (handled by spec 002-embedding-and-storage)
- OCR for scanned/image-based PDFs
- DOCX, XLSX, or other file format support
- Document versioning or content updates
- Document deletion (deferred to Phase 2; the schema uses `ON DELETE CASCADE` so a future `DELETE /api/v1/documents/{id}` endpoint requires no schema change)
- Metadata extraction beyond filename, page numbers, and section headers
- Content-based deduplication (only file-hash deduplication)
