# Embedding and Storage Notes

## Research Links
- [BAAI/bge-base-en-v1.5 on Hugging Face](https://huggingface.co/BAAI/bge-base-en-v1.5) — Model card, usage instructions, MTEB scores
- [sentence-transformers documentation](https://www.sbert.net/docs/sentence_transformer/usage/usage.html) — SentenceTransformer API, batch encoding, normalization
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard) — Embedding model benchmark comparison
- [pgvector GitHub](https://github.com/pgvector/pgvector) — Extension installation, HNSW parameters, performance benchmarks
- [pgvector HNSW benchmarks](https://github.com/pgvector/pgvector#hnsw) — Recall vs speed at various scales
- [ANN Benchmarks](https://ann-benchmarks.com/) — Comparing HNSW implementations across databases

## Design Discussions

### Why bge-base-en-v1.5 over other models?
`BAAI/bge-base-en-v1.5` (768d, 110M params) was selected over alternatives:
- **vs all-MiniLM-L6-v2** (384d): bge-base has significantly higher MTEB scores (63.55 vs ~56), justifying the larger model size for better retrieval quality.
- **vs bge-large-en-v1.5** (1024d, 335M params): The large variant has marginally better scores but requires ~1.3GB memory and ~150ms/chunk on CPU — too heavy for low-end machines.
- **vs OpenAI text-embedding-3-small** (1536d): Comparable retrieval quality, but bge-base runs locally (free, offline, private) vs API-only. The 768d dimensionality also halves storage requirements.
- **vs e5-base-v2** (768d): bge-base has higher MTEB scores (63.55 vs ~61).

The 768d output provides an excellent quality/storage balance — half the dimensions of the previous 1536d model with minimal quality loss for retrieval tasks.

### HNSW Parameter Selection
- **m=16**: The default. Higher values improve recall but increase index build time and memory. 16 provides good recall (>95%) at 100K scale.
- **ef_construction=64**: The default. Higher values improve recall during index build. 64 is sufficient for Phase 1.
- **ef_search=40**: Query-time parameter. Higher values improve recall at the cost of query latency. 40 provides ~95% recall with < 20ms latency at 100K vectors.

These parameters should be validated with real data in Phase 2. The pgvector documentation recommends increasing `ef_search` if recall seems low.

### Embedding Column as Nullable
The `embedding` column is nullable to support the two-phase ingestion pipeline: chunks are first created with NULL embeddings (spec 001), then embeddings are populated (this spec). This also provides a natural way to identify chunks that need embedding (WHERE embedding IS NULL) if the process is interrupted.

### Query Instruction Prefix
`bge-base-en-v1.5` recommends prepending an instruction prefix to queries for retrieval tasks: `"Represent this sentence for searching relevant passages: "`. This improves retrieval quality by ~1-2% on benchmarks. Document/passage texts do NOT get the prefix. The v1.5 model works reasonably well without the prefix (unlike v1), so it is recommended but not critical.

### Batch Size Selection
`sentence-transformers` `model.encode()` accepts a `batch_size` parameter (default 32). For CPU inference:
- **batch_size=32**: Good balance of throughput and memory. Processes 50 chunks in ~3-5 seconds.
- Larger batches may increase peak memory usage but don't significantly improve CPU throughput (unlike GPU).
- The entire chunk list can be passed to `encode()` at once; it handles batching internally.

### Memory Budget
The embedding model (`bge-base-en-v1.5`, ~440MB) and cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`, ~200MB) are both loaded at startup. Total model memory: ~640MB. This is acceptable for most machines with 4GB+ RAM. On very constrained systems, consider using `bge-small-en-v1.5` (33M params, ~130MB) as a lighter alternative.

## Lessons Learned
*(To be filled during implementation)*

## Open Questions
- Should we pre-warm the HNSW index after bulk inserts to improve first-query latency?
- Is the default `ef_search=40` sufficient for our recall requirements, or should we benchmark with 64 or 100?
- Should we implement a background job to verify embedding completeness (detect chunks with NULL embeddings)?
- Should the model be downloaded automatically on first startup, or require manual pre-download?
- Should we support GPU acceleration for embedding inference when available (auto-detect CUDA)?
