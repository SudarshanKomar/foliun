# Observability Specification

## Context
A RAG system has many invisible failure modes: degraded retrieval quality, slow pipeline stages, silent embedding errors, and LLM hallucinations. Without comprehensive observability, these issues are undetectable until users report poor answers. The system must provide structured logging, latency tracking, and pipeline diagnostics to enable rapid debugging and quality assessment.

Phase 1 observability focuses on structured logging with JSON format, correlation IDs for request tracing, per-stage latency tracking, and log-based metrics. Prometheus/Grafana dashboards are deferred to Phase 2.

This is a cross-cutting spec that applies to all other specs. It defines the logging standards, metric collection points, and diagnostic data that every component must produce.

## Requirements

### Functional Requirements
- FR-1: All log entries must be structured JSON with fields: `timestamp`, `level`, `correlation_id`, `message`, and context-specific fields.
- FR-2: Each API request must be assigned a unique correlation ID that propagates through all downstream operations (worker jobs, external API calls).
- FR-3: Log ingestion pipeline stages with document_id, stage name, duration, and outcome (success/failure).
- FR-4: Log query pipeline stages with correlation_id, stage name, duration, and diagnostic data:
    - **Query rewrite**: original query, generated variants, latency
    - **Embedding**: query count, latency
    - **Vector search**: query count, results per query, latency
    - **RRF fusion**: total candidates, unique candidates, latency
    - **Reranking**: candidates scored, top score, threshold applied, reranking_skipped flag, latency
    - **Context construction**: chunks included, total tokens, latency
    - **LLM synthesis**: model used, first token latency, total latency
- FR-5: Log all external API calls (OpenAI, Ollama) with request type, latency, status, and error details.
- FR-6: Track and log the following metrics per query (Phase 1 via logs, Phase 2 via Prometheus):
    - End-to-end query latency
    - Per-stage latency breakdown
    - Number of chunks retrieved, reranked, and included in context
    - Cross-encoder score distribution (min, max, mean of top 10)
    - Model used (gpt-4o-mini or gemma-4-2b)
    - Insufficient context rate (boolean per query)
- FR-7: Track and log the following metrics per ingestion job:
    - Total ingestion duration
    - Per-stage duration (extraction, chunking, embedding, storage)
    - Chunk count produced
    - Embedding model used and inference latency
    - Success/failure outcome
    - Retry count
- FR-8: Document status tracking must be queryable via API: users can see `pending → processing → ready/failed` transitions via `GET /api/v1/documents/{id}/status`.
- FR-9: Log configuration values at application startup (excluding secrets).

### Non-Functional Requirements
- NFR-1: Logging must not add > 5ms latency to any pipeline stage.
- NFR-2: Log volume must be manageable: INFO level by default, DEBUG available for troubleshooting.
- NFR-3: Structured logs must be parseable by standard log aggregation tools (ELK, CloudWatch, Datadog).
- NFR-4: Correlation IDs must be unique across all requests and traceable across API server and worker processes.
- NFR-5: Sensitive data (API keys, file content, embedding vectors) must NEVER appear in logs.

## Constraints
- **No external monitoring infrastructure** in Phase 1. All metrics are emitted via structured logs.
- **No distributed tracing** (e.g., OpenTelemetry). Correlation IDs provide basic tracing.
- **No alerting**. Phase 2 can add Prometheus alerting rules.
- **Python logging module** with JSON formatter. No external logging SDKs.

## Failure Cases
- **Logging failure** (e.g., disk full, stdout closed): Must not crash the application. Fail silently.
- **Correlation ID missing**: Generate a new one and log a warning. Never proceed without a correlation ID.
- **Large log entries**: Truncate chunk content and embedding vectors. Max log entry size: 10KB.

## Success Criteria
- Every API request has a corresponding log entry with correlation ID, status, and latency.
- Every ingestion job has per-stage log entries with document ID and duration.
- Every query has per-stage log entries traceable by correlation ID.
- Logs are valid JSON parseable by `jq` and standard log aggregation tools.
- No API keys, file contents, or embedding vectors appear in any log at any level.
- A developer can trace a single query from API request through all pipeline stages using grep on correlation ID.

## Out of Scope
- Prometheus metrics endpoint (Phase 2)
- Grafana dashboards (Phase 2)
- Distributed tracing with OpenTelemetry (Phase 2)
- Automated alerting (Phase 2)
- User-facing analytics or usage dashboards
- Log rotation and retention policies (handled by deployment infrastructure)
