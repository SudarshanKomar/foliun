# Observability Notes

## Research Links
- [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html) — Structured logging patterns, filters, formatters
- [python-json-logger](https://github.com/madzak/python-json-logger) — Library for JSON-formatted log output (alternative to custom formatter)
- [structlog](https://www.structlog.org/) — Structured logging library for Python (heavier alternative)
- [12 Factor App: Logs](https://12factor.net/logs) — Treat logs as event streams, write to stdout
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) — Future distributed tracing reference (Phase 2)

## Design Discussions

### Custom JSON Formatter vs structlog vs python-json-logger
Three approaches for structured JSON logging:

1. **Custom `logging.Formatter`** (chosen): Minimal dependency, full control over format, easy to understand. ~30 lines of code.
2. **python-json-logger**: Small library that patches the standard formatter. Saves ~10 lines of code but adds a dependency.
3. **structlog**: Feature-rich structured logging library with context variables, processors, and formatters. Overkill for Phase 1.

We chose the custom formatter to minimize dependencies and maintain full control. If structured logging needs grow (Phase 2), migrating to structlog is straightforward.

### Correlation ID Format
Format: `req-{8_hex_chars}` (e.g., `req-a1b2c3d4`)

- 8 hex characters = 32 bits of entropy = ~4 billion unique IDs
- Sufficient for Phase 1 (no risk of collision at low volume)
- Short enough to grep efficiently in log files
- `req-` prefix distinguishes from other IDs (document IDs, chunk IDs)

For ingestion worker jobs, the same correlation ID from the upload request is passed through the arq job payload, enabling cross-process tracing.

### What NOT to Log
Strict rules for preventing data leaks:

| Data Type | Rule | Reason |
|-----------|------|--------|
| API keys (`API_KEY`, `OPENAI_API_KEY`) | Never log | Security |
| File content (raw bytes) | Never log | Size, privacy |
| Embedding vectors (1536-dim arrays) | Never log | Size (6KB per vector) |
| Full chunk text | Truncate to 100 chars at INFO | Size |
| Query text | Truncate to 200 chars at INFO | Privacy |
| Full LLM prompts | DEBUG only, truncated | Size |
| Full LLM responses | DEBUG only, truncated | Size |

### Log-Based Metrics Strategy (Phase 1)
Without Prometheus, we extract metrics by parsing structured logs. Example `jq` queries:

```bash
# Average query latency (p50, p95)
cat app.log | jq -r 'select(.message == "Request completed" and .data.path == "/api/v1/query") | .data.latency_ms'

# Ingestion success rate
cat app.log | jq -r 'select(.message == "Ingestion job complete") | .data.status'

# Cross-encoder score distribution
cat app.log | jq -r 'select(.message == "Cross-encoder reranking completed") | .data.top_score'

# Insufficient context rate
cat app.log | jq -r 'select(.message == "Insufficient context") | .correlation_id'
```

Phase 2 replaces this with Prometheus counters/histograms and Grafana dashboards.

### Latency Measurement Approach
Use `time.perf_counter()` for high-resolution timing within a single process. This measures wall-clock time including I/O waits (which is what we want for external API calls). For CPU-bound stages (cross-encoder), this accurately reflects real latency.

Do NOT use `time.time()` — it has lower resolution and can jump due to NTP adjustments.

## Lessons Learned
*(To be filled during implementation)*

## Open Questions
- Should we emit a summary log entry per query with all stage latencies in a single record (for easier analysis)?
- Should we log the number of tokens in the LLM response (requires counting after stream completion)?
- Should we implement a log sampling mechanism for high-volume deployments (e.g., log 10% of DEBUG entries)?
- How should we handle log output in test environments (suppress to avoid noise, or redirect to file)?
