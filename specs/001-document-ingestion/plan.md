# Document Ingestion Implementation Plan

## Architecture Overview
Document ingestion spans two containers from the system architecture:

1. **FastAPI Server**: Receives uploads, validates files, stores to filesystem, creates DB records, enqueues jobs, serves status/list endpoints.
2. **Ingestion Worker** (arq): Picks up jobs from Redis, extracts text, chunks text, enriches metadata, writes chunks to PostgreSQL.

The boundary between sync (API) and async (worker) processing occurs at the Redis job queue. The API handles everything up to file storage and job enqueue; the worker handles everything from text extraction onward.

Reference: `/docs/architecture/system-overview.md` — Container View, Ingestion State Machine

## Data Flow

### Upload Flow (Synchronous — API Server)
1. Client sends `POST /api/v1/documents` with file as multipart/form-data
2. API extracts file from request, reads filename and content bytes
3. **Validation** (< 100ms):
   - Check MIME type: `application/pdf` or `text/plain`
   - Check file size: ≤ 50MB (52,428,800 bytes)
   - Check non-empty: file size > 0
4. Compute SHA-256 hash of file content
5. **Duplicate check**: Query `documents` table for matching `(filename, file_hash)`
   - If match found: return `200 OK` with existing document record
6. Generate UUID for new document
7. Store file to `./storage/documents/{uuid}/{filename}`
8. Create `documents` record in PostgreSQL with status `pending`
9. Enqueue job to Redis via `arq` with `document_id` payload
10. Return `202 Accepted` with document ID and status URL

### Processing Flow (Asynchronous — Worker)
1. Worker dequeues job, loads document record from PostgreSQL
2. Update document status to `processing`
3. **Text extraction**:
   - PDF: Open with `fitz.open()`, iterate pages, extract text via `page.get_text("text")`
   - TXT: Read file content with UTF-8 encoding
   - Update `page_count` on document record (PDF only)
4. **Chunking**:
   - Initialize `RecursiveCharacterTextSplitter` with separators `["\n\n", "\n", ". ", " ", ""]`, chunk_size=512 tokens, chunk_overlap=102 tokens
   - Token counting via `tiktoken` with `cl100k_base` encoding
   - Split extracted text into chunks
5. **Metadata enrichment** (per chunk):
   - `document_title`: filename without extension
   - `page_number`: determined by character offset mapping to PDF pages
   - `section_header`: regex detection of heading patterns (lines that are short, capitalized, or followed by blank lines)
   - `chunk_index`: 0-based sequential counter
   - `char_start` / `char_end`: character offset in the original extracted text
6. **Persistence**: Batch INSERT chunks into `chunks` table (without embeddings — embedding column left NULL)
7. Update document status to `ready`

## API Design

### Endpoints

#### `POST /api/v1/documents` — Upload Document
**Auth**: API Key required

**Request**: `multipart/form-data`
```
Content-Type: multipart/form-data
X-API-Key: <api_key>

file: <binary file data>
```

**Response (202 Accepted)** — New document:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "research-paper.pdf",
  "status": "pending",
  "status_url": "/api/v1/documents/a1b2c3d4-e5f6-7890-abcd-ef1234567890/status",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Response (200 OK)** — Duplicate detected:
```json
{
  "id": "existing-uuid-here",
  "filename": "research-paper.pdf",
  "status": "ready",
  "duplicate": true,
  "status_url": "/api/v1/documents/existing-uuid-here/status",
  "created_at": "2025-01-10T08:00:00Z"
}
```

**Response (400 Bad Request)** — Validation error:
```json
{
  "error": "unsupported_file_type",
  "detail": "Only PDF and TXT files are supported. Received: application/msword"
}
```

#### `GET /api/v1/documents/{id}/status` — Get Ingestion Status
**Auth**: API Key required

**Response (200 OK)**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "research-paper.pdf",
  "status": "ready",
  "chunk_count": 47,
  "page_count": 12,
  "file_size_bytes": 1048576,
  "error_message": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:25Z"
}
```

**Response (404 Not Found)**:
```json
{
  "error": "document_not_found",
  "detail": "Document with ID 'invalid-uuid' not found"
}
```

#### `GET /api/v1/documents` — List Documents
**Auth**: API Key required

**Response (200 OK)**:
```json
{
  "documents": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "filename": "research-paper.pdf",
      "status": "ready",
      "chunk_count": 47,
      "page_count": 12,
      "file_size_bytes": 1048576,
      "created_at": "2025-01-15T10:30:00Z"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "filename": "notes.txt",
      "status": "processing",
      "chunk_count": null,
      "page_count": null,
      "file_size_bytes": 25600,
      "created_at": "2025-01-15T10:31:00Z"
    }
  ],
  "total": 2
}
```

## Storage Design

### Database Schema

#### `documents` table
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_hash VARCHAR(64) NOT NULL,  -- SHA-256 hex digest
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'ready', 'failed')),
    error_message TEXT,
    page_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_documents_filename_hash ON documents (filename, file_hash);
CREATE INDEX idx_documents_status ON documents (status);
```

#### `chunks` table (content and metadata only — embedding added by spec 002)
```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    page_number INTEGER,
    section_header VARCHAR(500),
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    embedding VECTOR(1536),  -- populated by spec 002
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_chunks_doc_index ON chunks (document_id, chunk_index);
CREATE INDEX idx_chunks_document_id ON chunks (document_id);
```

### File Storage
- **Base path**: `./storage/documents/`
- **Structure**: `./storage/documents/{document_uuid}/{original_filename}`
- **Permissions**: Read/write for application user only (0700 directory, 0600 files)
- **Retention**: Files kept indefinitely in Phase 1. No automatic cleanup.
- **Path safety**: Document UUID prevents path traversal; original filename is sanitized (remove `..`, `/`, null bytes)

## Pipeline Stages

### Stage 1: Validation (sync, API)
- **Input**: Uploaded file bytes, filename, content type
- **Processing**: Check MIME type, file size, non-empty, compute SHA-256 hash, check duplicate
- **Output**: Validated file metadata or 400 error
- **Duration**: < 100ms

### Stage 2: File Storage (sync, API)
- **Input**: Validated file bytes, generated UUID
- **Processing**: Create directory, write file to disk
- **Output**: File path on disk
- **Duration**: < 500ms for 50MB file

### Stage 3: Job Enqueue (sync, API)
- **Input**: Document ID
- **Processing**: Create document record (status: pending), enqueue to Redis
- **Output**: 202 response to client
- **Duration**: < 50ms

### Stage 4: Text Extraction (async, worker)
- **Input**: File path, MIME type
- **Processing**: PyMuPDF for PDF, direct read for TXT
- **Output**: Raw text string, page count
- **Duration**: ~2s for 10-page PDF

### Stage 5: Chunking (async, worker)
- **Input**: Raw text string
- **Processing**: Recursive character text splitting with tiktoken counting
- **Output**: List of chunk objects with content and positional metadata
- **Duration**: < 500ms for typical document

### Stage 6: Metadata Enrichment (async, worker)
- **Input**: Chunk list, document metadata, page-to-offset mapping
- **Processing**: Annotate each chunk with page number, section header, character offsets
- **Output**: Enriched chunk objects
- **Duration**: < 100ms

### Stage 7: Persistence (async, worker)
- **Input**: Enriched chunk objects
- **Processing**: Batch INSERT into `chunks` table
- **Output**: Chunks stored, document status updated to `ready`
- **Duration**: < 1s for 100 chunks

## Error Handling

| Stage | Error | HTTP Code | Behavior |
|-------|-------|-----------|----------|
| Validation | Invalid type | 400 | Return error immediately, no file stored |
| Validation | File too large | 400 | Return error immediately, no file stored |
| Validation | Empty file | 400 | Return error immediately, no file stored |
| File storage | Disk write failure | 500 | Return error, no job queued |
| Enqueue | Redis unavailable | 500 | Return error, file stored but no job |
| Extraction | PDF corrupted | — | Retry up to 3x, then mark `failed` |
| Extraction | Password-protected | — | Mark `failed` immediately (no retry) |
| Extraction | Zero text | — | Mark `failed` immediately (no retry) |
| Chunking | Zero chunks | — | Mark `failed` immediately (no retry) |
| Persistence | DB write failure | — | Retry up to 3x, then mark `failed` |

**Retry strategy**: Exponential backoff via `arq` — delays of 1s, 4s, 16s. Maximum 3 retries. Failed jobs set document status to `failed` with error message.

**Logging**: All errors logged as structured JSON with fields: `document_id`, `stage`, `error_type`, `error_message`, `attempt`, `timestamp`.

## Related ADRs
- ADR-001: Use PostgreSQL with pgvector for vector storage
- ADR-003: Use Redis with arq for job queue management
- ADR-007: Use recursive character text splitting for chunking
- ADR-009: Single worker process for ingestion and embedding
