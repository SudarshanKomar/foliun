# ADR-003: Use Redis with arq for Job Queue Management

## Status
Accepted

## Context
Document ingestion is a multi-step pipeline (extraction → chunking → embedding → storage) that takes 5-30 seconds depending on document size. This must not block the API request. The system needs a reliable job queue for asynchronous processing with retry support, exponential backoff, and job status tracking.

Candidates considered: Celery + Redis, Redis + arq, RabbitMQ, PostgreSQL-based queues (e.g., pgboss pattern).

## Decision
We will use **Redis as the message broker** with the **`arq` library** for async job management.

- `arq` worker process runs alongside the FastAPI server
- Jobs enqueued with document ID as payload
- Retry policy: 3 retries with exponential backoff (1s, 4s, 16s)
- Job results and status stored in Redis with configurable TTL
- Single worker process in Phase 1; `arq` supports horizontal scaling

## Consequences

### Positive
- `arq` is async-native (built on `asyncio`), matching FastAPI's concurrency model
- Minimal setup — Redis is the only dependency, already used for queue
- Built-in retry with backoff, job timeouts, and result storage
- Lightweight: ~500 lines of code, easy to understand and debug
- Supports multiple workers via separate processes if scaling is needed

### Negative
- Less feature-rich than Celery (no built-in periodic tasks, limited monitoring)
- No built-in dashboard like Celery's Flower (must query Redis directly)
- Redis is not a durable message broker — jobs can be lost on Redis crash (acceptable for Phase 1)
- Smaller community than Celery; fewer Stack Overflow answers

### Neutral
- Redis also serves as SSE message coordination layer, consolidating infrastructure
- Migration to Celery or a more robust queue is possible but requires code changes

## Related ADRs
- ADR-001: Use PostgreSQL with pgvector for vector storage
- ADR-009: Single worker process for ingestion and embedding
