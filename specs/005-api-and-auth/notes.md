# API Design and Authentication Notes

## Research Links
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) — API key and dependency injection patterns
- [FastAPI Custom Exception Handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/) — Consistent error formatting
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/) — CORS middleware configuration
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — Environment variable loading
- [secrets.compare_digest](https://docs.python.org/3/library/secrets.html#secrets.compare_digest) — Timing-safe comparison for API keys

## Design Discussions

### API Key vs Bearer Token
For Phase 1, a static API key via `X-API-Key` header is simpler than Bearer token because:
- No token generation, refresh, or expiration logic
- No user database required
- Works with any HTTP client without special auth flow
- `secrets.compare_digest` prevents timing attacks

Phase 2 can introduce Bearer tokens with JWT for per-user authentication without changing the middleware pattern — just replace the dependency.

### URL Path Versioning
We use `/api/v1/` prefix for versioning rather than header-based (`Accept: application/vnd.api.v1+json`) or query parameter (`?v=1`) because:
- Most intuitive and widely understood
- Clearly visible in documentation and logs
- Easy to route in reverse proxies
- FastAPI's router prefix makes this trivial

### Error Response Consistency
All errors use `{"error": "<code>", "detail": "<message>"}` format regardless of source (validation, auth, business logic, server error). This is achieved by:
1. Custom exception handlers for `HTTPException`, `RequestValidationError`
2. A catch-all handler for unhandled exceptions
3. Pydantic `ErrorResponse` model ensuring type safety

### Health Check Design
The health endpoint checks dependencies in two tiers:

**Required** (failure → 503 unhealthy):
1. **PostgreSQL**: Execute `SELECT 1` query. Measures connection pool health and latency.
2. **Redis**: Execute `PING` command. Measures queue availability.
3. **Ollama**: `GET {OLLAMA_BASE_URL}/api/tags`. Measures local LLM availability **and** verifies that the required `gemma4:2b` model is pulled and available. Ollama is **required** for default operation — if unavailable or the model is missing, the system cannot process queries. Report both service status and model availability in the health response.

**Optional** (reported for visibility only):
4. **OpenAI**: Only checked when `OPENAI_API_KEY` is configured. Make a lightweight API call (e.g., list models). Omitted from response if not configured.

If any **required** dependency is unhealthy, the overall status is `unhealthy` and returns `503`. There is no automatic fallback from Ollama to GPT-4o-mini (per ADR-013). This enables load balancer health checks and monitoring alerts.

Note: The embedding model (`BAAI/bge-base-en-v1.5`) is loaded in-process at startup and does not require a separate health check endpoint. If the model fails to load, the application will not start. The health endpoint implicitly confirms embedding availability by virtue of the application being running.

### Correlation IDs
Each request gets a unique correlation ID (`req-{uuid4_short}`), set in request state and propagated to all log entries, database queries, and downstream API calls. This enables tracing a single request through the full pipeline (API → worker → external APIs) for debugging.

## Lessons Learned
*(To be filled during implementation)*

## Open Questions
- Should we implement API key rotation support (accept both old and new key during transition)?
- Should we add a `X-Request-ID` response header for client-side correlation?
- Should the query endpoint return `202 Accepted` for async processing, or `200 OK` with SSE stream directly?
- Should we implement request body size limits beyond file size (e.g., max JSON body size)?
