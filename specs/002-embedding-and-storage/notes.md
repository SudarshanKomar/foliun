# Embedding and Storage Notes

## Research Links
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings) — Model specs, batch limits, pricing
- [pgvector GitHub](https://github.com/pgvector/pgvector) — Extension installation, HNSW parameters, performance benchmarks
- [pgvector HNSW benchmarks](https://github.com/pgvector/pgvector#hnsw) — Recall vs speed at various scales
- [tiktoken token counting](https://github.com/openai/tiktoken) — Accurate token counts for cost estimation
- [ANN Benchmarks](https://ann-benchmarks.com/) — Comparing HNSW implementations across databases

## Design Discussions

### Why text-embedding-3-small over text-embedding-3-large?
`text-embedding-3-large` produces 3072-dimensional vectors with marginally better benchmark scores. However, 1536d from `text-embedding-3-small` provides excellent quality at half the storage cost and faster index operations. For Phase 1's scale (100K chunks), the quality difference is negligible. The `small` model also costs less ($0.02/1M tokens vs $0.13/1M tokens).

### HNSW Parameter Selection
- **m=16**: The default. Higher values improve recall but increase index build time and memory. 16 provides good recall (>95%) at 100K scale.
- **ef_construction=64**: The default. Higher values improve recall during index build. 64 is sufficient for Phase 1.
- **ef_search=40**: Query-time parameter. Higher values improve recall at the cost of query latency. 40 provides ~95% recall with < 20ms latency at 100K vectors.

These parameters should be validated with real data in Phase 2. The pgvector documentation recommends increasing `ef_search` if recall seems low.

### Embedding Column as Nullable
The `embedding` column is nullable to support the two-phase ingestion pipeline: chunks are first created with NULL embeddings (spec 001), then embeddings are populated (this spec). This also provides a natural way to identify chunks that need embedding (WHERE embedding IS NULL) if the process is interrupted.

### Batch Size Tradeoff
OpenAI allows up to 2048 texts per embedding request. Larger batches reduce round trips but increase the blast radius of failures. A single batch failure requires re-embedding all texts in that batch. For Phase 1's typical document sizes (50-200 chunks), a single batch usually suffices.

### Cost Monitoring Strategy
At $0.02 per 1M tokens, costs are low for Phase 1. A structured log entry per document with token count and estimated cost is sufficient. Phase 2 can add Prometheus metrics for aggregate cost tracking.

## Lessons Learned
*(To be filled during implementation)*

## Open Questions
- Should we pre-warm the HNSW index after bulk inserts to improve first-query latency?
- Is the default `ef_search=40` sufficient for our recall requirements, or should we benchmark with 64 or 100?
- Should we implement a background job to verify embedding completeness (detect chunks with NULL embeddings)?
