# Embedding and Storage Specification

## Context
After document text is extracted and chunked (spec 001), each chunk must be converted into a 768-dimensional vector embedding for semantic similarity search. Embeddings are the bridge between text and vector retrieval — their quality directly determines retrieval relevance.

Embedding generation runs locally using `BAAI/bge-base-en-v1.5` via the `sentence-transformers` library (already a project dependency for the cross-encoder reranker). This eliminates external API dependencies, network latency, and per-token costs for the ingestion pipeline. The generated embeddings must be stored in pgvector with an HNSW index for efficient approximate nearest neighbor search during query processing.

This spec covers the embedding generation stage of the ingestion pipeline and the pgvector storage/indexing configuration. It is tightly coupled to spec 001 (which produces chunks) and spec 003 (which queries embeddings).

## Requirements

### Functional Requirements
- FR-1: Generate 768-dimensional vector embeddings for all chunks using `BAAI/bge-base-en-v1.5` via `sentence-transformers` (local CPU inference).
- FR-2: Batch embedding generation locally — process chunks in batches of up to 32 texts via `model.encode(texts, batch_size=32)`.
- FR-3: Store embeddings in the `chunks.embedding` column (VECTOR(768)) in pgvector.
- FR-4: Create an HNSW index on the `embedding` column with cosine distance operator, `m=16`, `ef_construction=64`.
- FR-5: Embedding generation is part of the same arq job as text extraction and chunking (single worker pipeline per ADR-009).
- FR-6: After successful embedding storage, update document status to `ready`.
- FR-7: Support configurable `ef_search` parameter for query-time accuracy/speed tradeoff (default: 40).
- FR-8: Use the same embedding model (`BAAI/bge-base-en-v1.5`) for both chunk embeddings and query embeddings (query embedding handled by spec 003).
- FR-9: Load the embedding model once at application startup and keep it in memory (~440MB). Same lifecycle pattern as the cross-encoder reranker.
- FR-10: Validate at startup that the embedding model produces 768-dimensional vectors and that any existing embeddings in the database are compatible (same dimensionality).

### Non-Functional Requirements
- NFR-1: Embedding generation for a 10-page PDF (~50 chunks) must complete in < 15 seconds on CPU (local batch inference).
- NFR-2: HNSW index must support 100K+ vectors with < 20ms query latency per search.
- NFR-3: Embedding failures must trigger job retry (up to 3 times with exponential backoff).
- NFR-4: Embedding model must load in < 10 seconds at application startup.
- NFR-5: Embedding storage must use batch INSERT for efficiency (not individual inserts per chunk).

## Constraints
- **Model**: `BAAI/bge-base-en-v1.5` — the **only** embedding model for Phase 1. No OpenAI fallback.
- **Dimensions**: **768** (fixed). All embeddings must be 768-dimensional. The pgvector column and HNSW index are configured for 768d.
- **Dependency**: Requires chunks to be created first (spec 001). Embedding is the final stage of the ingestion pipeline.
- **Compute**: Local inference runs on CPU. The model (~440MB) must fit in available memory alongside the cross-encoder reranker (~200MB).
- **Cost**: Free. No per-token charges. Hardware-only cost.

## Failure Cases
- **Model load failure**: Application fails to start. Log critical error with model name and path. Common cause: insufficient memory or corrupted model cache.
- **Embedding inference error**: Retry with exponential backoff. After 3 retries, mark document as `failed` with error `"Embedding generation failed after 3 attempts"`.
- **Chunk text exceeds model token limit (512)**: Should not occur (chunks are 512 tokens), but if it does, truncate to 512 tokens and log a warning.
- **pgvector storage failure**: Retry entire embedding batch. On final failure, mark as `failed`.
- **Partial batch failure**: If some embeddings succeed but storage fails, the entire batch is retried (embeddings are regenerated — local inference is deterministic).
- **Startup validation failure**: If the model produces vectors with unexpected dimensions, or existing database embeddings have incompatible dimensions, the application logs a critical error and refuses to start.

## Success Criteria
- All chunks for a successfully ingested document have non-NULL `embedding` values.
- Embedding dimensions are exactly 768 per chunk.
- HNSW index is functional: a vector similarity query returns results in < 20ms for 100K chunks.
- A 10-page PDF's embeddings are generated and stored in < 15 seconds on CPU.
- Embedding model loads at startup in < 10 seconds.
- Document status transitions to `ready` only after all embeddings are stored.

## Out of Scope
- Fine-tuning the embedding model on domain-specific data (Phase 2)
- Re-embedding existing chunks when switching models (requires document re-ingestion)
- Embedding caching (embeddings are deterministic for same input)
- Query embedding generation (handled by spec 003-retrieval-pipeline)
- GPU acceleration for embedding inference (Phase 2)
