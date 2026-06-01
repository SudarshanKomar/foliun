# API Design and Authentication Implementation Tasks

## Phase 1: Foundation
- [ ] Create FastAPI application with lifespan handler for startup/shutdown (estimate: 1.5h)
- [ ] Set up Pydantic Settings class with environment variable loading (estimate: 1h)
- [ ] Create router modules: documents.py, query.py, health.py (estimate: 1h)
- [ ] Set up Uvicorn configuration with host, port, workers (estimate: 0.5h)
- [ ] Create Pydantic request/response schemas: DocumentUploadResponse, DocumentStatusResponse, DocumentListResponse, QueryRequest, ErrorResponse (estimate: 2h)
- [ ] Set up database session dependency with async SQLAlchemy (estimate: 2h)
- [ ] Set up OpenAI async client dependency (estimate: 0.5h)

## Phase 2: Core Implementation
- [ ] Implement API key authentication dependency using secrets.compare_digest (estimate: 1.5h)
- [ ] Implement custom exception handlers for 400, 401, 404, 500 with consistent ErrorResponse format (estimate: 2h)
- [ ] Implement Pydantic validation error handler to convert to ErrorResponse format (estimate: 1h)
- [ ] Implement request logging middleware: method, path, status, latency, correlation ID (estimate: 2h)
- [ ] Implement correlation ID generation and propagation via request state (estimate: 1h)
- [ ] Implement `GET /api/v1/health` endpoint: check PostgreSQL, Redis, Ollama (all required); check OpenAI only when OPENAI_API_KEY configured (estimate: 2h)
- [ ] Implement CORS middleware with configurable origins from environment variable (estimate: 0.5h)
- [ ] Register all routers under `/api/v1/` prefix (estimate: 0.5h)
- [ ] Implement 404 handler for undefined routes (estimate: 0.5h)
- [ ] Add `X-Accel-Buffering: no` header to SSE responses for proxy compatibility (estimate: 0.5h)
- [ ] Configure API key to not appear in OpenAPI docs or error responses (estimate: 0.5h)

## Phase 3: Testing & Refinement
- [ ] Unit test: API key authentication — valid key, invalid key, missing key, timing-safe comparison (estimate: 1.5h)
- [ ] Unit test: error response format — verify all error codes return consistent JSON structure (estimate: 1.5h)
- [ ] Unit test: request validation — query length limits, missing fields, invalid JSON (estimate: 1.5h)
- [ ] Unit test: health check — all healthy, partial failure, all failed (estimate: 1.5h)
- [ ] Integration test: full request lifecycle — upload, status, list, query (estimate: 3h)
- [ ] Integration test: CORS headers are correctly set for configured origins (estimate: 0.5h)
- [ ] Integration test: OpenAPI docs accessible at /docs and schemas are accurate (estimate: 1h)
- [ ] Security test: verify API key not present in logs, error responses, or OpenAPI docs (estimate: 1h)
- [ ] Load test: 10 concurrent requests to verify concurrency support (estimate: 1.5h)

## Phase 4: Documentation & Cleanup
- [ ] Verify auto-generated OpenAPI documentation is complete and accurate (estimate: 1h)
- [ ] Document environment variables and configuration in README (estimate: 1h)
- [ ] Create example API client script (curl or Python) for quick testing (estimate: 1h)
- [ ] Document error codes and their meanings (estimate: 0.5h)
