# ADR-014: Migrate to Local Embedding Model (BAAI/bge-base-en-v1.5)

## Status
Accepted

## Context
ADR-004 established OpenAI `text-embedding-3-small` (1536 dimensions) as the embedding model. While this provides high-quality embeddings via API, it introduces several issues that conflict with the project's evolving direction toward local-first operation:

1. **Hard dependency on OpenAI API**: Embedding generation requires internet connectivity and an active OpenAI API key. This prevents offline operation and creates a single point of failure for the entire ingestion pipeline.
2. **Cost**: While low ($0.02/1M tokens), embedding costs accumulate as the document corpus grows. A free local model eliminates this cost entirely.
3. **Privacy**: All document text is sent to OpenAI for embedding. For users with sensitive research documents, this expands the data exposure surface unnecessarily. A local model keeps all document content on the user's infrastructure.
4. **Architectural consistency**: ADR-013 established Ollama (Gemma 4 2B) as the default LLM, creating a local-first architecture for inference. Embeddings should follow the same pattern: local-only, with no cloud dependency.
5. **Vendor lock-in**: Dependence on OpenAI for both LLM and embeddings concentrates risk. Diversifying to a local embedding model reduces this.

The `sentence-transformers` library is already a project dependency (used for the cross-encoder reranker in spec 003), so adding a local embedding model introduces no new library dependencies.

## Decision
We will **replace OpenAI `text-embedding-3-small` with `BAAI/bge-base-en-v1.5`** as the default embedding model.

- **Model**: `BAAI/bge-base-en-v1.5` via `sentence-transformers` library
- **Dimensionality**: **768 dimensions** (down from 1536)
- **Parameters**: 110M — runs efficiently on CPU (~440MB memory)
- **Max sequence length**: 512 tokens (matches chunk size exactly)
- **License**: MIT — fully open-source, no restrictions
- **Query instruction**: For retrieval tasks, prepend `"Represent this sentence for searching relevant passages: "` to queries. Documents/passages use no prefix.
- **Loading**: Model loaded once at application startup (same pattern as cross-encoder reranker), cached in memory
- **Batch inference**: `model.encode(texts, batch_size=32)` for efficient local batch processing

### Model Selection Rationale

| Model | Dims | MTEB Avg | Params | CPU Speed | Verdict |
|-------|------|----------|--------|-----------|---------|
| **BAAI/bge-base-en-v1.5** | **768** | **63.55** | **110M** | **~50ms/chunk** | **Selected — best quality/size balance** |
| all-MiniLM-L6-v2 | 384 | ~56 | 22M | ~10ms/chunk | Fast but significantly lower retrieval quality |
| intfloat/e5-base-v2 | 768 | ~61 | 110M | ~50ms/chunk | Good but lower MTEB score |
| nomic-embed-text-v1 | 768 | ~62 | 137M | ~60ms/chunk | Requires `trust_remote_code`; less proven |
| BAAI/bge-small-en-v1.5 | 384 | 62.17 | 33M | ~15ms/chunk | Good speed but lower dimensionality |

`bge-base-en-v1.5` was selected because:
- Highest MTEB score among base-sized models (63.55)
- 768 dimensions provides a good balance — half the storage of 1536d while maintaining excellent retrieval quality
- 110M parameters runs comfortably on CPU (no GPU required)
- 512 token max sequence length matches our chunk size exactly
- MIT license with no usage restrictions
- Widely adopted in production RAG systems, extensively benchmarked
- Compatible with `sentence-transformers` (already a dependency for the cross-encoder reranker)

### Embedding Model Configuration
- **Model**: `BAAI/bge-base-en-v1.5` — the **only** embedding model for Phase 1
- **No OpenAI fallback**: There is no `EMBEDDING_MODEL` toggle. All embeddings use the local model. This avoids dimensional incompatibility (768d vs 1536d) and simplifies the architecture.
- **Critical constraint**: The same model must be used for both chunk embeddings (ingestion) and query embeddings (retrieval). The model is fixed at deployment time.
- **Tokenizer**: The embedding model's BERT WordPiece tokenizer (`AutoTokenizer.from_pretrained("BAAI/bge-base-en-v1.5")`) is used as the system-wide tokenizer for chunk sizing and context budget calculation. This ensures token counts align exactly with the model's 512 token limit.

### Migration Impact
- **pgvector column**: `VECTOR(1536)` → `VECTOR(768)`
- **HNSW index**: Same parameters (m=16, ef_construction=64) — these are scale-dependent, not dimension-dependent
- **Storage**: ~50% reduction (768 × 4 bytes = 3KB per vector vs 6KB)
- **Re-indexing**: Required — existing 1536d embeddings are incompatible with 768d model. Since the system is not yet implemented, this has no impact.

## Consequences

### Positive
- **True offline operation**: Embedding generation works without internet. Combined with Ollama for LLM, the system can run fully offline.
- **Zero cost**: No per-token embedding charges. Hardware-only cost.
- **Privacy**: Document text never leaves the user's infrastructure during embedding.
- **Reduced storage**: 768d vectors are 50% smaller than 1536d, reducing pgvector storage and HNSW index size.
- **No API rate limits**: Local inference has no rate limiting or throttling.
- **Faster for small batches**: No network round-trip latency for embedding calls.
- **No external dependency for ingestion**: Ingestion pipeline completes entirely locally (no OpenAI calls needed).

### Negative
- **CPU load**: Embedding generation uses CPU (110M parameter forward pass). ~50ms per chunk, ~3-5 seconds for 50 chunks (batched). Slower than API for very large batches.
- **Memory**: Model requires ~440MB RAM while loaded. This is in addition to the cross-encoder reranker (~200MB).
- **Slightly lower quality**: `bge-base-en-v1.5` (MTEB 63.55) scores lower than `text-embedding-3-small` (MTEB ~62.3 on v1, but competitive on retrieval-specific benchmarks). For this project's scale and use case, the quality difference is negligible.
- **First-load latency**: Model must be downloaded on first use (~440MB). Subsequent startups load from cache (~2-3 seconds).
- **Fixed dimensionality**: The system is hardcoded to 768d vectors. Changing the embedding model in the future requires re-embedding all chunks (see Migration Procedure below).

### Neutral
- The `sentence-transformers` library is already a project dependency (used for the cross-encoder reranker). No new library installation needed.
- OpenAI API key is only required if the user opts in to GPT-4o-mini for LLM. It is not needed for any embedding operation.
- The query instruction prefix for `bge-base-en-v1.5` is optional (v1.5 works well without it), but recommended for retrieval tasks to maximize quality.

### Re-Embedding Migration Procedure
If the embedding model is changed in a future phase:
1. Stop the ingestion worker to prevent new embeddings
2. Set all `chunks.embedding` to NULL: `UPDATE chunks SET embedding = NULL;`
3. Drop the existing HNSW index: `DROP INDEX idx_chunks_embedding_hnsw;`
4. Alter the vector column if dimensionality changes: `ALTER TABLE chunks ALTER COLUMN embedding TYPE VECTOR(new_dim);`
5. Re-embed all chunks using the new model (background job)
6. Recreate the HNSW index: `CREATE INDEX CONCURRENTLY ...`
7. Verify all chunks have non-NULL embeddings
8. Resume normal operation

## Related ADRs
- ADR-004: Superseded by this ADR (ADR-014)
- ADR-001: Use PostgreSQL with pgvector for vector storage (VECTOR dimension changes from 1536 to 768)
- ADR-013: Switch from E2B to Ollama for Local LLM (establishes the local-first pattern this ADR follows)
- ADR-009: Single worker process for ingestion and embedding (embedding is now local CPU instead of API call)
