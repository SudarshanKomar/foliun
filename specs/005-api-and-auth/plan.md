# API Design and Authentication Implementation Plan

## Architecture Overview
The API layer is implemented as a FastAPI application with the following structure:

```
app/
├── main.py              # FastAPI app, lifespan, middleware
├── config.py            # Environment variables, settings
├── dependencies.py      # Auth, DB session, OpenAI client DI
├── routers/
│   ├── documents.py     # Document upload, status, list
│   ├── query.py         # Query endpoint with SSE
│   └── health.py        # Health check
├── schemas/
│   ├── documents.py     # Pydantic models for document API
│   ├── query.py         # Pydantic models for query API
│   └── common.py        # Shared error models
└── middleware/
    └── logging.py       # Request logging middleware
```

All routes are registered under `/api/v1/` prefix. Authentication is implemented as a FastAPI dependency injected into route handlers.

Reference: `/docs/architecture/system-overview.md` — API Interface Summary, Component View

## Data Flow

### Request Lifecycle
1. Client sends HTTP request
2. Logging middleware records method, path, start time
3. CORS middleware processes headers (if configured)
4. Route handler invoked
5. Auth dependency validates `X-API-Key` (if required)
6. Request body validated via Pydantic model
7. Business logic executed (delegates to specs 001-004)
8. Response serialized and returned
9. Logging middleware records status code and latency

## API Design

### Complete Endpoint Reference

#### `POST /api/v1/documents` — Upload Document
Defined in spec 001-document-ingestion. Accepts multipart/form-data.

**Request**:
```
POST /api/v1/documents HTTP/1.1
Content-Type: multipart/form-data; boundary=---boundary
X-API-Key: sk-abc123

---boundary
Content-Disposition: form-data; name="file"; filename="paper.pdf"
Content-Type: application/pdf

<binary data>
---boundary--
```

**Responses**: `202 Accepted`, `200 OK` (duplicate), `400 Bad Request`, `401 Unauthorized`, `500 Internal Server Error`

#### `GET /api/v1/documents` — List Documents
Defined in spec 001-document-ingestion.

**Request**:
```
GET /api/v1/documents HTTP/1.1
X-API-Key: sk-abc123
```

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
    }
  ],
  "total": 1
}
```

#### `GET /api/v1/documents/{id}/status` — Document Status
Defined in spec 001-document-ingestion.

**Response (200 OK)**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "filename": "research-paper.pdf",
  "status": "processing",
  "chunk_count": null,
  "page_count": null,
  "file_size_bytes": 1048576,
  "error_message": null,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:05Z"
}
```

#### `POST /api/v1/query` — Submit Query
Defined in specs 003 and 004.

**Request**:
```json
{
  "query": "What are the main findings of the research paper?",
  "model": "gemma-4-2b"
}
```

**Pydantic Schema**:
```python
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    model: Literal["gemma-4-2b", "gpt-4o-mini"] = "gemma-4-2b"
```

**Response (200 OK, SSE Stream)**:
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no

event: token
data: {"content": "The research paper"}

event: token
data: {"content": " primarily focuses on"}

event: token
data: {"content": " three key findings"}

event: done
data: {"sources_used": 2, "chunks_in_context": 5, "model": "gemma-4-2b", "latency_ms": 3500}
```

**Response (200 OK, Insufficient Context)**:
```json
{
  "insufficient_context": true,
  "message": "No relevant documents found for your query. Try uploading documents related to your question.",
  "query": "What is the weather on Mars?"
}
```

#### `GET /api/v1/health` — Health Check
**No authentication required.**

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "postgresql": {"status": "connected", "latency_ms": 5},
    "redis": {"status": "connected", "latency_ms": 2},
    "ollama": {"status": "reachable", "latency_ms": 10},
    "openai": {"status": "reachable", "latency_ms": 150}
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```
Notes:
- **Ollama** is always checked (required for default LLM operation). Health checked via `GET {OLLAMA_BASE_URL}/api/tags`.
- **OpenAI** is only checked when `OPENAI_API_KEY` is configured. Omitted from response otherwise.
- If any required dependency (PostgreSQL, Redis, Ollama) is down, overall status is `unhealthy` (503).

**Response (503 Service Unavailable)**:
```json
{
  "status": "unhealthy",
  "version": "1.0.0",
  "dependencies": {
    "postgresql": {"status": "connected", "latency_ms": 5},
    "redis": {"status": "disconnected", "error": "Connection refused"},
    "ollama": {"status": "reachable", "latency_ms": 10}
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Consistent Error Response Schema
```python
class ErrorResponse(BaseModel):
    error: str       # Machine-readable error code (e.g., "unauthorized", "validation_error")
    detail: str      # Human-readable error description

# HTTP status mapping:
# 400 → validation_error, unsupported_file_type, file_too_large, empty_file, invalid_request
# 401 → unauthorized
# 404 → not_found, document_not_found
# 500 → internal_error
# 503 → service_unavailable
```

## Storage Design
This spec does not define storage. Authentication uses a single environment variable (`API_KEY`). No database tables for auth in Phase 1.

### Configuration (Environment Variables)
```
API_KEY=sk-your-secret-key-here        # Required
DATABASE_URL=postgresql://...           # Required
REDIS_URL=redis://localhost:6379       # Required
OPENAI_API_KEY=sk-...                  # Optional (required only if user opts in to GPT-4o-mini LLM)
OLLAMA_BASE_URL=http://localhost:11434    # Default shown. Ollama is required for default operation.
CORS_ORIGINS=http://localhost:3000     # Optional, comma-separated
STORAGE_PATH=./storage/documents       # Optional, default shown
LOG_LEVEL=INFO                         # Optional, default INFO
```

## Pipeline Stages

### Authentication Pipeline
1. Extract `X-API-Key` from request headers
2. Compare against `API_KEY` environment variable (constant-time comparison)
3. If missing: raise `HTTPException(401, "Missing X-API-Key header")`
4. If invalid: raise `HTTPException(401, "Invalid API key")`
5. If valid: proceed to route handler

```python
async def verify_api_key(x_api_key: str = Header(...)):
    if not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=401,
            detail=ErrorResponse(error="unauthorized", detail="Invalid API key").dict()
        )
```

### Request Logging Pipeline
1. Record: timestamp, method, path, client IP
2. Execute request
3. Record: status code, response time
4. Log as structured JSON

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "method": "POST",
  "path": "/api/v1/query",
  "status": 200,
  "latency_ms": 3500,
  "correlation_id": "req-a1b2c3d4"
}
```

## Error Handling

| Scenario | HTTP Status | Error Code | Detail |
|----------|-------------|------------|--------|
| Missing API key | 401 | `unauthorized` | "Missing X-API-Key header" |
| Invalid API key | 401 | `unauthorized` | "Invalid API key" |
| Invalid JSON | 400 | `invalid_request` | "Request body must be valid JSON" |
| Missing required field | 400 | `validation_error` | "Field 'query' is required" |
| Query too long | 400 | `validation_error` | "Query must be between 1 and 2000 characters" |
| Unsupported file type | 400 | `unsupported_file_type` | "Only PDF and TXT files are supported" |
| File too large | 400 | `file_too_large` | "File size exceeds 50MB limit" |
| Document not found | 404 | `document_not_found` | "Document with ID '{id}' not found" |
| Endpoint not found | 404 | `not_found` | "Endpoint not found" |
| Server error | 500 | `internal_error` | "An unexpected error occurred" |
| Dependency down | 503 | `service_unavailable` | "{service} temporarily unavailable" |

**Security**: API key values are NEVER included in error responses or logs. Stack traces are logged server-side but not returned to clients.

## Related ADRs
- ADR-002: Use FastAPI as the backend framework
- ADR-008: Use Server-Sent Events for response streaming
- ADR-010: Use API key authentication for Phase 1
- ADR-013: Switch from E2B to Ollama (Gemma 4 2B) for Local LLM (supersedes ADR-011)
- ADR-014: Migrate to Local Embedding Model (BAAI/bge-base-en-v1.5) (supersedes ADR-004)
