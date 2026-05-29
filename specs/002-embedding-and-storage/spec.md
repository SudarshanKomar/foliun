# Embedding and Storage Specification

## Context
After document text is extracted and chunked (spec 001), each chunk must be converted into a 1536-dimensional vector embedding for semantic similarity search. Embeddings are the bridge between text and vector retrieval — their quality directly determines retrieval relevance.

Embedding generation is the most latency-sensitive and cost-bearing step in the ingestion pipeline. It requires external API calls to OpenAI, introduces network latency, and incurs per-token costs. The generated embeddings must be stored in pgvector with an HNSW index for efficient approximate nearest neighbor search during query processing.

This spec covers the embedding generation stage of the ingestion pipeline and the pgvector storage/indexing configuration. It is tightly coupled to spec 001 (which produces chunks) and spec 003 (which queries embeddings).

## Requirements

### Functional Requirements
- FR-1: Generate 1536-dimensional vector embeddings for all chunks using OpenAI `text-embedding-3-small` API.
- FR-2: Batch embedding requests to OpenAI API — up to 2048 texts per request to minimize API calls and latency.
- FR-3: Store embeddings in the `chunks.embedding` column (VECTOR(1536)) in pgvector.
- FR-4: Create an HNSW index on the `embedding` column with cosine distance operator, `m=16`, `ef_construction=64`.
- FR-5: Embedding generation is part of the same arq job as text extraction and chunking (single worker pipeline per ADR-009).
- FR-6: After successful embedding storage, update document status to `ready`.
- FR-7: Support configurable `ef_search` parameter for query-time accuracy/speed tradeoff (default: 40).
- FR-8: Use the same embedding model (`text-embedding-3-small`) for both chunk embeddings and query embeddings (query embedding handled by spec 003).

### Non-Functional Requirements
- NFR-1: Embedding generation for a 10-page PDF (~50 chunks) must complete in < 10 seconds (single batch API call).
- NFR-2: HNSW index must support 100K+ vectors with < 20ms query latency per search.
- NFR-3: Embedding API failures must trigger job retry (up to 3 times with exponential backoff).
- NFR-4: OpenAI API rate limit errors (429) must be handled with retry-after backoff.
- NFR-5: Embedding storage must use batch INSERT for efficiency (not individual inserts per chunk).

## Constraints
- **Model**: OpenAI `text-embedding-3-small` only. No model selection or fallback in Phase 1.
- **Dimensions**: 1536 (full dimensionality, no reduction).
- **Dependency**: Requires chunks to be created first (spec 001). Embedding is the final stage of the ingestion pipeline.
- **Network**: Requires internet connectivity to reach OpenAI API. No offline embedding generation.
- **Cost**: ~$0.02 per 1M tokens. A 10-page PDF (~25K tokens) costs ~$0.0005 to embed.

## Failure Cases
- **OpenAI API timeout**: Retry with exponential backoff. After 3 retries, mark document as `failed` with error `"Embedding generation timed out after 3 attempts"`.
- **OpenAI API rate limit (429)**: Respect `Retry-After` header. Delay and retry.
- **OpenAI API error (500)**: Retry with backoff. After 3 retries, mark as `failed`.
- **Invalid API key**: Mark document as `failed` with error `"OpenAI API authentication failed"`. No retry.
- **Chunk text exceeds model token limit (8191)**: Should not occur (chunks are 512 tokens), but if it does, truncate to 8191 tokens and log a warning.
- **pgvector storage failure**: Retry entire embedding batch. On final failure, mark as `failed`.
- **Partial batch failure**: If some embeddings succeed but storage fails, the entire batch is retried (embeddings are regenerated — OpenAI calls are idempotent).

## Success Criteria
- All chunks for a successfully ingested document have non-NULL `embedding` values.
- Embedding dimensions are exactly 1536 per chunk.
- HNSW index is functional: a vector similarity query returns results in < 20ms for 100K chunks.
- A 10-page PDF's embeddings are generated and stored in < 10 seconds.
- OpenAI API rate limits are handled gracefully without job failure.
- Document status transitions to `ready` only after all embeddings are stored.

## Out of Scope
- Embedding model selection or switching (Phase 2)
- Dimensionality reduction (using `text-embedding-3-small`'s `dimensions` parameter)
- Re-embedding existing chunks (requires document re-ingestion)
- Embedding caching (embeddings are deterministic for same input)
- Query embedding generation (handled by spec 003-retrieval-pipeline)
