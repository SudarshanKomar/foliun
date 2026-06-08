# ADR-002: Use FastAPI as the Backend Framework

## Status
Accepted

## Context
The backend framework must support asynchronous request handling (for parallel vector searches and LLM API calls), Server-Sent Events for streaming responses, and modern Python type hints for API contract enforcement. The system is a REST API-first application with no server-rendered UI in Phase 1.

Candidates considered: FastAPI, Flask, Django, Starlette (raw).

## Decision
We will use **FastAPI (Python 3.14)** as the backend framework.

- All API endpoints defined with Pydantic models for request/response validation
- Async route handlers for non-blocking I/O (OpenAI API calls, database queries)
- `StreamingResponse` with async generators for SSE streaming
- Dependency injection for database sessions, auth, and configuration
- Uvicorn as the ASGI server

## Consequences

### Positive
- Native async/await support eliminates thread pool bottlenecks for I/O-bound operations
- Automatic OpenAPI documentation generated from Pydantic models
- Type-safe request validation reduces runtime errors
- Strong ecosystem: `httpx` for async HTTP, `asyncpg` for database, `arq` for queue
- Fast development velocity with excellent documentation

### Negative
- Python's GIL limits CPU-bound parallelism (cross-encoder reranking runs sequentially)
- Async programming model has a learning curve and debugging complexity
- No built-in background task framework (requires `arq` for job queue)

### Neutral
- FastAPI is built on Starlette; migration to raw Starlette is trivial if needed
- Python 3.14 offers improved performance over earlier versions

## Related ADRs
- ADR-008: Use Server-Sent Events for response streaming
- ADR-010: Use API key authentication for Phase 1
