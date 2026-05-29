# ADR-008: Use Server-Sent Events for Response Streaming

## Status
Accepted

## Context
LLM-generated answers are produced token-by-token and should be streamed to the client in real-time to reduce perceived latency. The system needs a mechanism to push tokens from the server to the client as they are generated. The streaming protocol must work with standard HTTP infrastructure (proxies, load balancers) and be supported by modern browsers.

Candidates considered: Server-Sent Events (SSE), WebSockets, HTTP/2 Server Push, long polling.

## Decision
We will use **Server-Sent Events (SSE)** over HTTP/1.1 for streaming LLM responses.

- FastAPI `StreamingResponse` with `text/event-stream` content type
- Async generator yields SSE-formatted events as LLM tokens arrive
- Event types: `token` (content), `citation` (source reference), `done` (stream complete), `error` (failure)
- Connection timeout: 120 seconds (accommodates slow LLM responses)
- Client reconnection handled by browser's native `EventSource` API

## Consequences

### Positive
- Simple implementation: FastAPI's `StreamingResponse` + async generator
- Unidirectional (server → client) matches the streaming use case perfectly
- Native browser support via `EventSource` API — no additional client libraries needed
- Works over standard HTTP/1.1 — compatible with all proxies and load balancers
- Automatic reconnection built into the EventSource specification
- Lower complexity than WebSockets (no connection upgrade, no ping/pong)

### Negative
- Unidirectional only — cannot receive client messages during streaming (e.g., cancel request)
- Limited to text-based data (no binary streaming)
- Some older proxy configurations may buffer SSE responses (requires `X-Accel-Buffering: no` header)
- No built-in message acknowledgment — if the client disconnects, tokens are lost

### Neutral
- WebSockets would be needed for bidirectional communication (e.g., chat with interruption) but are overkill for Phase 1's request-response streaming model
- Migration to WebSockets in Phase 2+ is straightforward if bidirectional communication is needed

## Related ADRs
- ADR-002: Use FastAPI as the backend framework
- ADR-011: Use GPT-4o-mini as primary LLM
