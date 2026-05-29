# ADR-010: Use API Key Authentication for Phase 1

## Status
Accepted

## Context
The API must be protected from unauthorized access. Phase 1 targets single-user or small-team usage, making a full authentication system (OAuth2, JWT, user management) unnecessarily complex. However, leaving the API completely open is unacceptable, especially since it proxies calls to paid external services (OpenAI) and local compute resources (Ollama).

The authentication mechanism must be simple to implement, easy to use from API clients, and sufficient for the Phase 1 threat model (trusted users, no multi-tenancy).

## Decision
We will use **static API key authentication** via the `X-API-Key` HTTP header.

- API key configured via environment variable `API_KEY`
- All endpoints except `GET /api/v1/health` require the `X-API-Key` header
- Invalid or missing key returns `401 Unauthorized` with JSON error body
- FastAPI dependency injection used for auth middleware
- Single shared API key for all users in Phase 1

## Consequences

### Positive
- Trivial to implement: one FastAPI dependency, one environment variable
- No database tables, no token rotation, no session management
- Works with all HTTP clients (curl, Postman, SDKs) without special configuration
- Sufficient security for Phase 1's single-user/small-team threat model
- Prevents accidental exposure of paid API proxying

### Negative
- No per-user identity — cannot track who made which request
- API key is a shared secret — if compromised, all access must be revoked
- No token expiration or rotation mechanism
- Not suitable for multi-tenant or public-facing deployments
- Transmitting API key in headers requires HTTPS in production

### Neutral
- Full RBAC, user management, and JWT-based authentication are deferred to Phase 2
- The API key pattern is a standard FastAPI middleware — migration to OAuth2/JWT requires replacing the dependency only

## Related ADRs
- ADR-002: Use FastAPI as the backend framework
