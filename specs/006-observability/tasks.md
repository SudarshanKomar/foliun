# Observability Implementation Tasks

## Phase 1: Foundation
- [ ] Create JSON log formatter class with timestamp, level, correlation_id, logger, message, data fields (estimate: 2h)
- [ ] Configure Python logging module with JSON formatter for stdout output (estimate: 1h)
- [ ] Create correlation ID generator utility: `req-{uuid4_hex[:8]}` format (estimate: 0.5h)
- [ ] Create `LogContext` helper for attaching correlation_id and data to log records (estimate: 1.5h)
- [ ] Configure log levels: INFO default, DEBUG via LOG_LEVEL environment variable (estimate: 0.5h)

## Phase 2: Core Implementation
- [ ] Implement request logging middleware: assign correlation_id, log method/path/status/latency on completion (estimate: 2h)
- [ ] Add `X-Correlation-ID` response header to all responses (estimate: 0.5h)
- [ ] Implement correlation ID propagation to arq job payload for ingestion worker (estimate: 1h)
- [ ] Implement ingestion pipeline stage logging: extraction, chunking, embedding, storage with per-stage latency (estimate: 3h)
- [ ] Implement query pipeline stage logging: rewrite, embed, search, RRF, rerank, context, synthesis with per-stage latency (estimate: 4h)
- [ ] Implement external API call logging wrapper for OpenAI calls (service, operation, latency, status) (estimate: 1.5h)
- [ ] Implement external API call logging wrapper for Ollama calls (estimate: 1h)
- [ ] Implement embedding performance tracking log entry: document_id, chunks, embedding_model, latency_ms (estimate: 0.5h)
- [ ] Implement first-token latency tracking for LLM streaming responses (estimate: 1h)
- [ ] Implement sensitive data filtering: ensure API keys, file content, embedding vectors never logged (estimate: 1.5h)
- [ ] Implement log entry size guard: truncate chunk content to 100 chars, cap entries at 10KB (estimate: 1h)
- [ ] Log application configuration at startup (excluding secrets) (estimate: 0.5h)
- [ ] Implement insufficient context event logging with max_score and threshold (estimate: 0.5h)
- [ ] Implement citation validation warning logging (estimate: 0.5h)

## Phase 3: Testing & Refinement
- [ ] Unit test: JSON formatter produces valid JSON for all log levels (estimate: 1h)
- [ ] Unit test: correlation ID generation is unique and correctly formatted (estimate: 0.5h)
- [ ] Unit test: sensitive data filter blocks API keys, embeddings, file content (estimate: 1.5h)
- [ ] Unit test: log entry size truncation works for oversized payloads (estimate: 1h)
- [ ] Integration test: correlation ID propagates from API request through pipeline stages (estimate: 2h)
- [ ] Integration test: correlation ID propagates from upload request through arq worker job (estimate: 2h)
- [ ] Integration test: full query pipeline produces all expected stage log entries (estimate: 2h)
- [ ] Integration test: full ingestion pipeline produces all expected stage log entries (estimate: 2h)
- [ ] Verification test: grep correlation ID from logs retrieves all stages of a single request (estimate: 1h)
- [ ] Verification test: parse all log output with `jq` to confirm valid JSON (estimate: 0.5h)

## Phase 4: Documentation & Cleanup
- [ ] Document log format specification with field descriptions and examples (estimate: 1h)
- [ ] Document correlation ID format and propagation mechanism (estimate: 0.5h)
- [ ] Document log level guidelines (what goes at INFO vs DEBUG vs WARNING) (estimate: 0.5h)
- [ ] Create sample `jq` queries for common debugging scenarios (estimate: 1h)
