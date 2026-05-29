# API Design and Authentication Specification

## Context
The AI Research Workspace exposes a REST API as the primary interface for document ingestion, querying, and system health monitoring. All API endpoints must follow consistent conventions for request/response format, error handling, and authentication. This spec defines the cross-cutting API concerns that span all other specs.

Phase 1 uses static API key authentication — sufficient for single-user or small-team usage. The API must be well-structured to support future evolution (RBAC, OAuth2 in Phase 2) without breaking changes.

This spec is the integration point for all other specs: it defines the external API contracts that specs 001-004 implement internally.

## Requirements

### Functional Requirements
- FR-1: All API endpoints use JSON request/response bodies (except file upload which uses multipart/form-data and query response which uses SSE).
- FR-2: All endpoints are versioned under `/api/v1/` prefix.
- FR-3: All endpoints except `GET /api/v1/health` require API key authentication via `X-API-Key` header.
- FR-4: API key is configured via `API_KEY` environment variable. Missing or invalid key returns `401 Unauthorized`.
- FR-5: `GET /api/v1/health` returns system health status including dependency connectivity (PostgreSQL, Redis, OpenAI API, and Ollama when configured).
- FR-6: All error responses use a consistent JSON format: `{"error": "<error_code>", "detail": "<human_readable_message>"}`.
- FR-7: All successful responses include appropriate HTTP status codes: `200 OK`, `202 Accepted` (async operations), `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, `500 Internal Server Error`, `503 Service Unavailable`.
- FR-8: Request validation errors return `400` with specific field-level error messages.
- FR-9: Query length is limited to 2000 characters. Queries exceeding this return `400`.
- FR-10: All responses include `Content-Type` header: `application/json` for JSON, `text/event-stream` for SSE.
- FR-11: CORS headers are configurable via environment variables for frontend integration.

### Non-Functional Requirements
- NFR-1: API server must start and be ready to serve requests within 30 seconds (including model loading).
- NFR-2: Health endpoint must respond in < 500ms.
- NFR-3: API must support 10+ concurrent connections.
- NFR-4: All requests must be logged with method, path, status code, and latency.
- NFR-5: API key must not appear in logs or error responses.

## Constraints
- **Framework**: FastAPI with Uvicorn ASGI server.
- **Authentication**: Static API key only. No user sessions, no JWT, no OAuth2.
- **Versioning**: URL path versioning (`/api/v1/`). No header-based versioning.
- **No breaking changes**: API contracts defined here are stable for Phase 1. Additive changes (new fields, new endpoints) are allowed.

## Failure Cases
- **Missing API key**: Return `401 Unauthorized` with `{"error": "unauthorized", "detail": "Missing X-API-Key header"}`.
- **Invalid API key**: Return `401 Unauthorized` with `{"error": "unauthorized", "detail": "Invalid API key"}`.
- **Invalid JSON body**: Return `400 Bad Request` with `{"error": "invalid_request", "detail": "Request body must be valid JSON"}`.
- **Missing required field**: Return `400 Bad Request` with `{"error": "validation_error", "detail": "Field 'query' is required"}`.
- **Query too long**: Return `400 Bad Request` with `{"error": "validation_error", "detail": "Query must be between 1 and 2000 characters"}`.
- **Endpoint not found**: Return `404 Not Found` with `{"error": "not_found", "detail": "Endpoint not found"}`.
- **Server error**: Return `500 Internal Server Error` with `{"error": "internal_error", "detail": "An unexpected error occurred"}`. Log full stack trace.
- **Dependency unavailable**: Return `503 Service Unavailable` with `{"error": "service_unavailable", "detail": "Required service temporarily unavailable"}`.

## Success Criteria
- All 5 endpoints respond with correct status codes for valid and invalid requests.
- Authentication blocks requests without valid API key on protected endpoints.
- Health endpoint returns accurate dependency status.
- Error responses are consistent in format across all endpoints.
- API key is never logged or returned in error responses.
- OpenAPI documentation is automatically generated and accessible at `/docs`.

## Out of Scope
- User management and RBAC (Phase 2)
- OAuth2 / JWT authentication (Phase 2)
- API rate limiting (Phase 2)
- API key rotation (Phase 2)
- Pagination for document list (sufficient for Phase 1 scale)
- WebSocket endpoints
