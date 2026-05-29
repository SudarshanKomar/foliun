# ADR-009: Single Worker Process for Ingestion and Embedding

## Status
Accepted

## Context
The document ingestion pipeline consists of sequential stages: text extraction → chunking → metadata enrichment → embedding generation → vector storage. An earlier design proposed separate Ingestion and Embedding workers, but this introduces inter-worker coordination complexity (signaling when chunking is complete, tracking partial progress across workers, handling split failures).

The Phase 1 system targets modest scale (1,000 documents, 100K chunks) with single-user or small-team usage.

## Decision
We will use a **single worker process** that handles the entire ingestion pipeline end-to-end.

- One `arq` worker process handles extraction, chunking, and embedding in a single job
- Chunks are embedded immediately after creation within the same job execution
- No inter-worker messaging or coordination required
- Worker can be scaled horizontally by running multiple `arq` worker instances if throughput is insufficient

## Consequences

### Positive
- No inter-worker coordination — eliminates an entire class of distributed systems bugs
- Simplified error handling: if any stage fails, the entire job retries from the beginning
- Easier debugging: single log stream per document, single failure point
- Reduced infrastructure: one process type instead of two
- `arq` supports multiple concurrent workers trivially (just run more processes)

### Negative
- If embedding generation fails, text extraction and chunking are repeated on retry (wasted work)
- Single worker cannot parallelize extraction and embedding across different documents (sequential per job)
- Long-running jobs (large PDFs) hold the worker; other documents wait in queue

### Neutral
- Partial progress tracking is still implemented: document status transitions through `pending → processing → ready/failed`
- Can be split into separate workers in Phase 2 if bottleneck analysis shows embedding is the dominant cost
- The re-extraction cost on retry is negligible compared to embedding API latency

## Related ADRs
- ADR-003: Use Redis with arq for job queue management
- ADR-004: Use OpenAI text-embedding-3-small for embeddings
