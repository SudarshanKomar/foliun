# Observability Implementation Plan

## Architecture Overview
Observability is implemented as a cross-cutting concern using Python's built-in `logging` module with a JSON formatter. It consists of three layers:

1. **Request logging middleware** (API layer): Captures HTTP method, path, status, latency, correlation ID for every request.
2. **Pipeline stage logging** (business logic): Captures per-stage timing and diagnostic data for ingestion and query pipelines.
3. **External call logging** (integration layer): Captures latency, status, and errors for OpenAI and Ollama API calls.

Correlation IDs tie all log entries for a single request together, enabling end-to-end tracing via log search.

Reference: `/docs/architecture/system-overview.md` — Non-Functional Requirements: Observability

## Data Flow

### Correlation ID Propagation
```
Client Request
  └── API Middleware assigns correlation_id = "req-{uuid4_short}"
       ├── stores in request.state.correlation_id
       ├── passes to pipeline functions as parameter
       ├── includes in arq job payload (for async ingestion)
       └── all log calls include correlation_id field
```

For synchronous query pipeline:
- Correlation ID is generated at request entry and passed through all function calls.

For asynchronous ingestion pipeline:
- Correlation ID is generated at upload request, stored in the arq job payload, and extracted by the worker.

### Log Entry Format
```json
{
  "timestamp": "2025-01-15T10:30:00.123Z",
  "level": "INFO",
  "correlation_id": "req-a1b2c3d4",
  "logger": "app.retrieval.reranker",
  "message": "Cross-encoder reranking completed",
  "data": {
    "candidates_scored": 30,
    "top_score": 0.87,
    "threshold": 0.5,
    "chunks_above_threshold": 8,
    "latency_ms": 420
  }
}
```

### Log Levels

| Level | Usage |
|-------|-------|
| **ERROR** | Unrecoverable failures: database errors, OpenAI auth failures, file system errors |
| **WARNING** | Recoverable issues: reranking timeout (fallback to RRF), query rewrite failure (fallback to original), invalid citation detected, retry attempt |
| **INFO** | Normal operations: request completed, ingestion stage completed, query stage completed, document status change |
| **DEBUG** | Detailed diagnostics: query variants generated, individual chunk scores, full SQL queries, raw API responses (truncated) |

## API Design
No new API endpoints. Observability is emitted via structured logs only in Phase 1.

### Health Endpoint Enhancement (spec 005)
The existing `GET /api/v1/health` endpoint reports dependency status, which serves as a basic monitoring probe.

## Storage Design
No additional storage. Logs are written to stdout/stderr for capture by deployment infrastructure (Docker logs, systemd journal, CloudWatch, etc.).

### Log Output Configuration
```python
import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "correlation_id": getattr(record, "correlation_id", None),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "data"):
            log_entry["data"] = record.data
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)
```

## Pipeline Stages

### Stage 1: Request Logging Middleware
Wraps every HTTP request.

```python
@app.middleware("http")
async def log_request(request: Request, call_next):
    correlation_id = f"req-{uuid4().hex[:8]}"
    request.state.correlation_id = correlation_id
    start = time.perf_counter()
    
    response = await call_next(request)
    
    latency_ms = (time.perf_counter() - start) * 1000
    logger.info("Request completed", extra={
        "correlation_id": correlation_id,
        "data": {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": round(latency_ms, 1),
        }
    })
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

### Stage 2: Ingestion Pipeline Logging
Each stage of the ingestion pipeline logs its entry, exit, and any errors.

| Log Point | Level | Key Fields |
|-----------|-------|------------|
| Job started | INFO | `document_id`, `filename` |
| Extraction complete | INFO | `document_id`, `page_count`, `text_length`, `latency_ms` |
| Chunking complete | INFO | `document_id`, `chunk_count`, `avg_tokens`, `latency_ms` |
| Embedding batch sent | INFO | `document_id`, `batch_size`, `total_tokens`, `latency_ms` |
| Embedding cost | INFO | `document_id`, `total_tokens`, `estimated_cost_usd` |
| Storage complete | INFO | `document_id`, `chunks_stored`, `latency_ms` |
| Job complete | INFO | `document_id`, `total_latency_ms`, `status: ready` |
| Stage failure | ERROR | `document_id`, `stage`, `error_type`, `error_message`, `attempt` |
| Retry scheduled | WARNING | `document_id`, `stage`, `attempt`, `next_delay_s` |

### Stage 3: Query Pipeline Logging
Each stage of the query pipeline logs diagnostics for retrieval quality analysis.

| Log Point | Level | Key Fields |
|-----------|-------|------------|
| Query received | INFO | `query` (first 200 chars), `model` |
| Rewrite complete | INFO | `variants` (list), `latency_ms` |
| Rewrite failed | WARNING | `error`, fallback to original |
| Embedding complete | INFO | `query_count`, `latency_ms` |
| Search complete | INFO | `results_per_query` (list), `total_results`, `latency_ms` |
| RRF fusion complete | INFO | `total_candidates`, `unique_candidates`, `top_30_rrf_scores` (min/max), `latency_ms` |
| Reranking complete | INFO | `candidates_scored`, `top_score`, `threshold`, `chunks_above`, `latency_ms` |
| Reranking skipped | WARNING | `reason` (timeout/error), fallback to RRF |
| Context built | INFO | `chunks_included`, `total_tokens`, `sources_count`, `latency_ms` |
| LLM synthesis start | INFO | `model`, `context_tokens` |
| LLM first token | INFO | `first_token_latency_ms` |
| LLM complete | INFO | `model`, `total_latency_ms`, `output_tokens` (estimated) |
| Insufficient context | INFO | `max_score`, `threshold`, query (first 200 chars) |
| Citation validation | WARNING | `invalid_citations` (list), if any detected |

### Stage 4: External API Call Logging
Wrapper for all OpenAI and Ollama API calls.

```python
async def log_external_call(
    service: str,  # "openai" or "ollama"
    operation: str,  # "embeddings", "chat.completions"
    correlation_id: str,
    call_fn: Callable,
) -> Any:
    start = time.perf_counter()
    try:
        result = await call_fn()
        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(f"{service} call completed", extra={
            "correlation_id": correlation_id,
            "data": {"service": service, "operation": operation, "latency_ms": round(latency_ms, 1), "status": "success"}
        })
        return result
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        logger.error(f"{service} call failed", extra={
            "correlation_id": correlation_id,
            "data": {"service": service, "operation": operation, "latency_ms": round(latency_ms, 1), "error": str(e)}
        })
        raise
```

## Error Handling
Logging must never cause application failures:
- All logging wrapped in try/except with fallback to `print()` to stderr
- Large payloads (chunk content, embeddings) truncated before logging
- Correlation ID absence triggers warning and auto-generation

### Sensitive Data Filtering
The following must NEVER appear in logs:
- `API_KEY`, `OPENAI_API_KEY` values
- Full document file contents
- Embedding vectors (1536-dimensional arrays)
- Full chunk text at INFO level (truncate to first 100 chars)

## Related ADRs
- ADR-002: Use FastAPI as the backend framework
- ADR-009: Single worker process for ingestion and embedding
